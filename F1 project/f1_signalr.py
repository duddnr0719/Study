"""
F1 Live Timing — SignalR 클라이언트 (인증 불필요)

livetiming.formula1.com/signalr 엔드포인트는 F1 계정 없이 접속 가능.
aiohttp WebSocket 클라이언트 사용 (websockets 라이브러리 불필요).

메시지 형식 (구 SignalR 프로토콜):
  {"C":"cursor", "M":[{"H":"Streaming","M":"feed","A":["TopicName", data, seq]}]}
  data는 JSON dict 또는 base64+zlib 압축 문자열.
"""

import asyncio
import json
import logging
import zlib
from base64 import b64decode
from typing import Any, Callable, Coroutine
from urllib.parse import quote

import aiohttp

logger = logging.getLogger("f1_signalr")

# ── 엔드포인트 ──────────────────────────────────────────────────────────
_BASE_URL      = "https://livetiming.formula1.com/signalr"
_WS_BASE_URL   = "wss://livetiming.formula1.com/signalr"
_CONNECTION_DATA = quote('[{"name":"Streaming"}]', safe='')

_TOPICS = [
    "TimingData",
    "TimingAppData",
    "CarData",
    "RaceControlMessages",
    "WeatherData",
    "SessionInfo",
    "TrackStatus",
    "DriverList",
]


# ── 압축 해제 헬퍼 ──────────────────────────────────────────────────────
def _decompress(data: str) -> Any:
    """F1 SignalR 메시지 데이터 압축 해제 (base64 + zlib deflate)."""
    try:
        raw = b64decode(data)
        return json.loads(zlib.decompress(raw, -zlib.MAX_WBITS).decode("utf-8"))
    except Exception:
        return data


class F1SignalRClient:
    """F1 SignalR 클라이언트 — 인증 불필요, 자동 재연결."""

    def __init__(self):
        self._running = False

    # ── 메인 루프 ────────────────────────────────────────────────────────
    async def run(
        self,
        on_message: Callable[[str, Any], Coroutine],
        reconnect_delay: float = 5.0,
    ) -> None:
        """SignalR 연결 유지 루프. 연결 끊김 시 자동 재연결."""
        self._running = True

        while self._running:
            try:
                connector = aiohttp.TCPConnector(ssl=True)
                # negotiate + WebSocket 을 같은 세션에서 실행 (쿠키 공유)
                async with aiohttp.ClientSession(connector=connector) as session:
                    # ── Negotiate ──────────────────────────────────────
                    neg_url = f"{_BASE_URL}/negotiate?connectionData={_CONNECTION_DATA}&clientProtocol=1.5"
                    resp = await session.get(neg_url, timeout=aiohttp.ClientTimeout(total=10))
                    resp.raise_for_status()
                    neg_data = await resp.json()
                    conn_token = neg_data.get("ConnectionToken", "")
                    if not conn_token:
                        logger.warning("Negotiate 실패 — ConnectionToken 없음")
                        await asyncio.sleep(reconnect_delay)
                        continue

                    encoded_token = quote(conn_token, safe="")
                    ws_url = (
                        f"{_WS_BASE_URL}/connect"
                        f"?transport=webSockets"
                        f"&clientProtocol=1.5"
                        f"&connectionToken={encoded_token}"
                        f"&connectionData={_CONNECTION_DATA}"
                    )
                    logger.info("F1 SignalR 연결 중...")

                    # ── WebSocket 연결 ─────────────────────────────────
                    async with session.ws_connect(
                        ws_url,
                        heartbeat=20,
                        timeout=aiohttp.ClientTimeout(total=None, connect=10),
                    ) as ws:
                        # 구 SignalR — 핸드셰이크 없음, 바로 구독
                        sub_msg = json.dumps({
                            "H": "Streaming",
                            "M": "Subscribe",
                            "A": [_TOPICS],
                            "I": 1,
                        })
                        await ws.send_str(sub_msg)
                        logger.info("F1 SignalR 구독 완료: %s", _TOPICS)

                        reconnect_delay = 5.0  # 성공 시 딜레이 리셋

                        # ── 수신 루프 ──────────────────────────────────
                        async for msg in ws:
                            if not self._running:
                                return

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                raw_text = msg.data
                            elif msg.type == aiohttp.WSMsgType.BINARY:
                                raw_text = msg.data.decode("utf-8", errors="replace")
                            elif msg.type in (
                                aiohttp.WSMsgType.CLOSE,
                                aiohttp.WSMsgType.ERROR,
                                aiohttp.WSMsgType.CLOSED,
                            ):
                                logger.warning("F1 SignalR 연결 닫힘: %s", msg.type)
                                break
                            else:
                                continue

                            try:
                                parsed = json.loads(raw_text)
                            except json.JSONDecodeError:
                                continue

                            # M 배열 — 실시간 데이터 메시지
                            for item in parsed.get("M", []):
                                if item.get("H") != "Streaming" or item.get("M") != "feed":
                                    continue
                                args = item.get("A", [])
                                if len(args) < 2:
                                    continue
                                topic   = args[0]   # "TimingData" etc.
                                payload = args[1]   # dict 또는 압축 문자열

                                # 압축 해제
                                if isinstance(payload, str):
                                    payload = _decompress(payload)

                                if isinstance(payload, dict):
                                    await on_message(topic, payload)

            except asyncio.CancelledError:
                logger.info("F1 SignalR 클라이언트 종료.")
                break
            except Exception as e:
                logger.warning("F1 SignalR 연결 끊김: %s. %ss 후 재연결...", e, reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60.0)  # exponential backoff

    def stop(self) -> None:
        self._running = False
