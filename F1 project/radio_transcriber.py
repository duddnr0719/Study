"""F1 팀 라디오 실시간 전사 파이프라인 (Step 3)

F1 TV Premium 인증 → 온보드 오디오 스트림 캡처 (FFmpeg/streamlink) → Faster-Whisper 전사
전사 결과는 live_state["team_radio"]에 누적됨.

필요 패키지 (requirements.txt에 추가):
  faster-whisper>=1.0.0
  streamlink>=7.0.0      # F1 TV 스트림 URL 추출용

필요 시스템 도구:
  ffmpeg  (brew install ffmpeg / apt-get install ffmpeg)

환경변수 (.env):
  F1TV_EMAIL       : F1 TV 계정 이메일
  F1TV_PASSWORD    : F1 TV 계정 비밀번호
  WHISPER_MODEL    : Faster-Whisper 모델 크기 (기본값: "medium")
  WHISPER_DEVICE   : "cuda" 또는 "cpu" (기본값: "cuda")
  WHISPER_COMPUTE  : "float16" 또는 "int8" (기본값: "float16")
  AUDIO_SEGMENT_S  : 오디오 세그먼트 길이 초 (기본값: 5)
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp

import live_state as ls

logger = logging.getLogger("radio_transcriber")

# ── F1 TV API 엔드포인트 ──────────────────────────────────────────────
_F1TV_AUTH_URL    = "https://api.formula1.com/v2/account/subscriber/authenticate/by-password"
_F1TV_IDEN_URL    = (
    "https://f1tv.formula1.com/api/identity-providers/"
    "iden_732298a17f9c458890a1877880d140f8/authenticate"
)
_F1TV_CONTENT_URL = "https://f1tv.formula1.com/2.0/R/ENG/BIG_SCREEN_HLS/ALL/CONTENT/PLAY"
_F1TV_HEADERS     = {
    "apikey": "fCUCjWrKPu9ylJwRAv8BpGLEgiAuThx7",
    "Content-Type": "application/json",
}

# ── Whisper 설정 ──────────────────────────────────────────────────────
_WHISPER_MODEL   = os.getenv("WHISPER_MODEL",   "medium")
_WHISPER_DEVICE  = os.getenv("WHISPER_DEVICE",  "cuda")
_WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE", "float16")
_SEGMENT_SECS    = int(os.getenv("AUDIO_SEGMENT_S", "5"))

# ── F1TV 채널 목록 API ────────────────────────────────────────────────
# 현재 라이브 이벤트의 온보드 채널을 나열함. 인증 헤더 필요.
_F1TV_LIVE_PAGE_URL = (
    "https://f1tv.formula1.com/2.0/R/ENG/BIG_SCREEN_HLS/ALL/PAGE/LIVE/F1_LIVE/2"
)
_CHANNEL_MAP_TTL = 300  # 5분 캐시 (세션 중에는 채널 ID가 불변)


class F1TVAuth:
    """F1 TV Premium 인증 — ascendon_token → session_token 흐름."""

    def __init__(self, email: str, password: str):
        self.email    = email
        self.password = password
        self._session_token: Optional[str] = None
        self._expires_at: float = 0.0

    @property
    def token(self) -> Optional[str]:
        return self._session_token

    def is_valid(self) -> bool:
        return bool(self._session_token) and time.time() < self._expires_at - 60

    async def authenticate(self, session: aiohttp.ClientSession) -> bool:
        """F1 TV Premium 2단계 인증. 성공 시 True 반환."""
        try:
            # Step 1: 계정 인증 → subscriptionToken (ascendon_token)
            async with session.post(
                _F1TV_AUTH_URL,
                json={"Login": self.email, "Password": self.password},
                headers=_F1TV_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("F1TV 계정 인증 실패 (HTTP %s)", resp.status)
                    return False
                data = await resp.json()
                ascendon = (
                    data.get("data", {}).get("subscriptionToken")
                    or data.get("subscriptionToken")
                )
                if not ascendon:
                    logger.warning("F1TV subscriptionToken 없음 (키: %s)", list(data.keys()))
                    return False

            # Step 2: ascendon_token → F1TV session_token
            async with session.post(
                _F1TV_IDEN_URL,
                json={
                    "identity_provider_url": _F1TV_AUTH_URL,
                    "ascendon_token": ascendon,
                },
                headers=_F1TV_HEADERS,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("F1TV 세션 토큰 발급 실패 (HTTP %s)", resp.status)
                    return False
                data = await resp.json()
                self._session_token = (
                    data.get("data", {}).get("token")
                    or data.get("token")
                )
                if not self._session_token:
                    logger.warning("F1TV session_token 없음 (키: %s)", list(data.keys()))
                    return False

            self._expires_at = time.time() + 3600  # 1시간 유효로 가정
            logger.info("F1TV 인증 성공")
            return True

        except Exception as e:
            logger.warning("F1TV 인증 오류: %s", e)
            return False


class RadioTranscriber:
    """
    F1 TV Premium 팀 라디오 → Faster-Whisper 실시간 전사.

    동작 흐름:
      1. F1TV 인증 (F1TVAuth)
      2. live_state["active"] 감지 → 세션 활성화 확인
      3. 드라이버별 온보드 스트림 URL 조회 (F1TV Content API 또는 streamlink)
      4. FFmpeg 서브프로세스로 오디오 세그먼트 추출 (16kHz mono WAV)
      5. Faster-Whisper로 전사 (GPU 활용)
      6. live_state["team_radio"]에 저장
    """

    def __init__(self):
        self._email    = os.getenv("F1TV_EMAIL",    "")
        self._password = os.getenv("F1TV_PASSWORD", "")
        self._running  = False
        self._auth     = F1TVAuth(self._email, self._password)
        self._model    = None   # lazy-loaded
        # {driver_number_str: content_id_str} — F1TV API 동적 조회 결과 캐시
        self._channel_map: dict[str, str] = {}
        self._channel_map_ts: float = 0.0

    # ── Whisper 모델 로드 ────────────────────────────────────────────────

    def _load_model(self) -> bool:
        """Faster-Whisper 모델을 GPU에 로드. 12GB VRAM 기준 medium 모델 권장."""
        if self._model is not None:
            return True
        try:
            from faster_whisper import WhisperModel  # type: ignore
            logger.info(
                "Faster-Whisper 모델 로딩: %s (%s / %s)",
                _WHISPER_MODEL, _WHISPER_DEVICE, _WHISPER_COMPUTE,
            )
            self._model = WhisperModel(
                _WHISPER_MODEL,
                device=_WHISPER_DEVICE,
                compute_type=_WHISPER_COMPUTE,
            )
            logger.info("Faster-Whisper 모델 로드 완료")
            return True
        except ImportError:
            logger.warning(
                "faster-whisper 미설치 — `pip install faster-whisper` 실행 필요"
            )
            return False
        except Exception as e:
            logger.warning("Faster-Whisper 모델 로드 실패: %s", e)
            return False

    # ── 전사 ─────────────────────────────────────────────────────────────

    def _transcribe_file(self, audio_path: str) -> str:
        """WAV 파일 → 전사 텍스트 반환 (동기, 별도 스레드에서 호출)."""
        if self._model is None:
            return ""
        try:
            segments, info = self._model.transcribe(
                audio_path,
                beam_size=5,
                language="en",
                condition_on_previous_text=False,
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.debug(
                "전사 완료 (lang=%s, prob=%.2f): %s",
                info.language, info.language_probability, text,
            )
            return text
        except Exception as e:
            logger.warning("전사 실패: %s", e)
            return ""

    # ── 드라이버 채널 맵 동적 조회 ──────────────────────────────────────

    async def _fetch_driver_channels(
        self,
        session: aiohttp.ClientSession,
    ) -> dict[str, str]:
        """
        F1TV Live Page API에서 온보드 채널 목록 조회.
        결과: {driver_number_str: content_id_str}
        5분 캐시 적용 — 세션 중 채널 ID는 불변.
        """
        # 캐시 유효하면 그대로 반환
        if self._channel_map and time.time() - self._channel_map_ts < _CHANNEL_MAP_TTL:
            return self._channel_map

        if not self._auth.token:
            return self._channel_map  # 인증 전 — 빈 맵 유지

        try:
            headers = {
                **_F1TV_HEADERS,
                "Authorization": f"Bearer {self._auth.token}",
            }
            async with session.get(
                _F1TV_LIVE_PAGE_URL,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    logger.debug("F1TV 채널 목록 조회 실패 (HTTP %s)", resp.status)
                    return self._channel_map
                data = await resp.json()

            # resultObj.containers 배열에서 온보드 채널 파싱
            containers = (
                data.get("resultObj", {})
                    .get("containers", [])
            )
            new_map: dict[str, str] = {}
            for container in containers:
                meta       = container.get("metadata", {})
                content_id = str(meta.get("contentId", ""))
                if not content_id:
                    continue

                # driverNumber는 properties 배열 또는 metadata에 위치
                driver_num = None
                for prop in container.get("properties", []):
                    if prop.get("driverNumber"):
                        driver_num = str(prop["driverNumber"])
                        break
                if not driver_num:
                    driver_num = str(meta.get("driverNumber", ""))

                # channelType "obc" (OnBoard Camera) 만 포함
                channel_type = ""
                for prop in container.get("properties", []):
                    if prop.get("channelType"):
                        channel_type = prop["channelType"].lower()
                        break

                if driver_num and channel_type == "obc":
                    new_map[driver_num] = content_id

            if new_map:
                self._channel_map    = new_map
                self._channel_map_ts = time.time()
                logger.info("F1TV 드라이버 채널 맵 갱신: %d개", len(new_map))
            else:
                logger.debug("F1TV 채널 목록 응답에서 obc 채널 없음 (containers=%d)", len(containers))

        except Exception as e:
            logger.debug("F1TV 채널 맵 조회 오류: %s", e)

        return self._channel_map

    # ── 스트림 URL 조회 ──────────────────────────────────────────────────

    async def _get_stream_url_via_api(
        self,
        session: aiohttp.ClientSession,
        content_id: str,
    ) -> Optional[str]:
        """F1 TV Content API로 HLS 스트림 URL 조회."""
        if not self._auth.token:
            return None
        try:
            headers = {
                **_F1TV_HEADERS,
                "Authorization": f"Bearer {self._auth.token}",
            }
            async with session.get(
                _F1TV_CONTENT_URL,
                headers=headers,
                params={"contentId": content_id, "channelId": ""},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return (
                    data.get("resultObj", {}).get("url")
                    or data.get("url")
                )
        except Exception as e:
            logger.debug("F1TV 스트림 URL 조회 실패 (content=%s): %s", content_id, e)
            return None

    async def _get_stream_url_via_streamlink(self, driver_num: str) -> Optional[str]:
        """streamlink F1 TV 플러그인으로 HLS URL 추출 (fallback)."""
        try:
            channel_id = self._channel_map.get(driver_num, "")
            f1tv_url = f"https://f1tv.formula1.com/detail/{channel_id}" if channel_id else ""
            if not f1tv_url:
                return None
            proc = await asyncio.create_subprocess_exec(
                "streamlink",
                "--stream-url",
                "--f1tv-email",    self._email,
                "--f1tv-password", self._password,
                f1tv_url,
                "best",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
            url = stdout.decode().strip()
            return url if url.startswith("http") else None
        except (asyncio.TimeoutError, FileNotFoundError):
            return None
        except Exception as e:
            logger.debug("streamlink URL 추출 실패 (드라이버 %s): %s", driver_num, e)
            return None

    # ── 오디오 캡처 + 전사 ──────────────────────────────────────────────

    async def _capture_and_transcribe(
        self,
        stream_url: str,
        driver_num: str,
    ) -> None:
        """
        FFmpeg로 _SEGMENT_SECS 분량 오디오 캡처 → Whisper 전사 → live_state 저장.
        임시 파일은 항상 삭제됨.
        """
        tmp_path = ""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                "ffmpeg", "-y",
                "-i",  stream_url,
                "-t",  str(_SEGMENT_SECS),   # 세그먼트 길이
                "-vn",                        # 비디오 제거
                "-ar", "16000",               # Whisper 권장 샘플레이트
                "-ac", "1",                   # 모노
                "-f",  "wav",
                tmp_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=_SEGMENT_SECS + 15,
            )
            if proc.returncode != 0:
                logger.debug(
                    "FFmpeg 비정상 종료 (드라이버 %s, rc=%s): %s",
                    driver_num, proc.returncode, stderr.decode()[-300:],
                )
                return

            # Whisper 전사는 동기 함수 → asyncio.to_thread로 event loop 블록 방지
            text = await asyncio.to_thread(self._transcribe_file, tmp_path)
            if not text:
                return

            entry = {
                "utc":    datetime.now(timezone.utc).isoformat(),
                "driver": driver_num,
                "text":   text,
            }
            async with ls.live_lock:
                ls.live_state["team_radio"].append(entry)

            logger.info("[팀 라디오] #%s: %s", driver_num, text)

        except asyncio.TimeoutError:
            logger.debug("FFmpeg 타임아웃 (드라이버 %s)", driver_num)
        except FileNotFoundError:
            logger.warning("ffmpeg 미설치 — `brew install ffmpeg` 실행 필요")
        except Exception as e:
            logger.debug("오디오 캡처 오류 (드라이버 %s): %s", driver_num, e)
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

    # ── 스트림 URL 결정 ──────────────────────────────────────────────────

    async def _resolve_stream_url(
        self,
        session: aiohttp.ClientSession,
        driver_num: str,
    ) -> Optional[str]:
        """
        드라이버 번호 → HLS 스트림 URL.
        우선순위: F1TV Content API (동적 채널맵) → streamlink 폴백.
        """
        # 채널 맵이 비어 있으면 먼저 갱신
        channel_map = await self._fetch_driver_channels(session)
        channel_id  = channel_map.get(driver_num)
        if channel_id:
            url = await self._get_stream_url_via_api(session, channel_id)
            if url:
                return url
        return await self._get_stream_url_via_streamlink(driver_num)

    # ── 메인 루프 ────────────────────────────────────────────────────────

    async def run(self, reconnect_delay: float = 10.0) -> None:
        """
        메인 루프 — F1TV 인증 유지 + 라이브 세션 감지 + 팀 라디오 전사.

        비활성화 조건:
          - F1TV_EMAIL / F1TV_PASSWORD 미설정
          - Faster-Whisper 모델 로드 실패
        """
        self._running = True

        if not self._email or not self._password:
            logger.warning(
                "F1TV_EMAIL / F1TV_PASSWORD 미설정 — 팀 라디오 파이프라인 비활성화"
            )
            return

        if not self._load_model():
            logger.warning("Whisper 모델 로드 실패 — 팀 라디오 파이프라인 비활성화")
            return

        connector = aiohttp.TCPConnector(ssl=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            while self._running:
                try:
                    # 인증 갱신
                    if not self._auth.is_valid():
                        ok = await self._auth.authenticate(session)
                        if not ok:
                            logger.warning(
                                "F1TV 인증 실패. %ss 후 재시도...", reconnect_delay
                            )
                            await asyncio.sleep(reconnect_delay)
                            reconnect_delay = min(reconnect_delay * 2, 120.0)
                            continue
                        reconnect_delay = 10.0  # 인증 성공 시 딜레이 리셋

                    # 활성 세션 대기
                    if not ls.live_state["active"]:
                        await asyncio.sleep(5)
                        continue

                    # 현재 세션 드라이버 목록 (상위 5명만 처리하여 부하 절감)
                    drivers = list(ls.live_state["drivers"].keys())[:5]
                    if not drivers:
                        await asyncio.sleep(5)
                        continue

                    # 드라이버별 스트림 URL 조회 + 동시 전사
                    url_tasks = [
                        self._resolve_stream_url(session, num) for num in drivers
                    ]
                    stream_urls = await asyncio.gather(*url_tasks, return_exceptions=True)

                    transcribe_tasks = []
                    for driver_num, url in zip(drivers, stream_urls):
                        if isinstance(url, str) and url.startswith("http"):
                            transcribe_tasks.append(
                                self._capture_and_transcribe(url, driver_num)
                            )

                    if transcribe_tasks:
                        await asyncio.gather(*transcribe_tasks, return_exceptions=True)

                    await asyncio.sleep(_SEGMENT_SECS)

                except asyncio.CancelledError:
                    logger.info("팀 라디오 파이프라인 종료")
                    break
                except Exception as e:
                    logger.warning(
                        "라디오 파이프라인 오류: %s. %ss 후 재시도...", e, reconnect_delay
                    )
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 120.0)

    def stop(self) -> None:
        self._running = False
