"""radio_transcriber 모듈 단위 테스트

실행:
  cd "F1 project"
  python -m pytest tests/ -v
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import radio_transcriber as rt
from radio_transcriber import F1TVAuth, RadioTranscriber, _find_bin


# ── _find_bin ────────────────────────────────────────────────────────────

class TestFindBin:
    def test_returns_system_path_if_found(self):
        """shutil.which가 결과를 반환하면 그 값을 그대로 사용."""
        with patch("radio_transcriber.shutil.which", return_value="/usr/bin/ffmpeg"):
            result = _find_bin("ffmpeg")
        assert result == "/usr/bin/ffmpeg"

    def test_falls_back_to_venv_bin(self, tmp_path):
        """시스템 PATH에 없으면 venv bin 디렉터리에서 찾음."""
        fake_bin = tmp_path / "streamlink"
        fake_bin.touch(mode=0o755)

        with patch("radio_transcriber.shutil.which", return_value=None), \
             patch("radio_transcriber.sys.executable", str(tmp_path / "python")):
            result = _find_bin("streamlink")

        assert result == str(fake_bin)

    def test_returns_name_when_not_found(self, tmp_path):
        """어디에도 없으면 원본 이름 반환 (FileNotFoundError 지점 명시용)."""
        with patch("radio_transcriber.shutil.which", return_value=None), \
             patch("radio_transcriber.sys.executable", str(tmp_path / "python")):
            result = _find_bin("nonexistent_tool")

        assert result == "nonexistent_tool"


# ── F1TVAuth ─────────────────────────────────────────────────────────────

class TestF1TVAuth:
    def _make_auth(self):
        return F1TVAuth("test@example.com", "secret")

    def test_initial_state_not_valid(self):
        auth = self._make_auth()
        assert auth.is_valid() is False
        assert auth.token is None

    def test_is_valid_after_token_set(self):
        auth = self._make_auth()
        auth._session_token = "tok"
        auth._expires_at = time.time() + 3600
        assert auth.is_valid() is True

    def test_is_invalid_when_expired(self):
        auth = self._make_auth()
        auth._session_token = "tok"
        auth._expires_at = time.time() - 1  # 이미 만료
        assert auth.is_valid() is False

    def test_authenticate_success(self):
        auth = self._make_auth()

        step1_resp = AsyncMock()
        step1_resp.status = 200
        step1_resp.json = AsyncMock(return_value={"data": {"subscriptionToken": "ascendon_abc"}})
        step1_resp.__aenter__ = AsyncMock(return_value=step1_resp)
        step1_resp.__aexit__ = AsyncMock(return_value=False)

        step2_resp = AsyncMock()
        step2_resp.status = 200
        step2_resp.json = AsyncMock(return_value={"data": {"token": "session_xyz"}})
        step2_resp.__aenter__ = AsyncMock(return_value=step2_resp)
        step2_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=[step1_resp, step2_resp])

        result = asyncio.run(auth.authenticate(mock_session))

        assert result is True
        assert auth.token == "session_xyz"
        assert auth.is_valid() is True

    def test_authenticate_step1_http_error(self):
        auth = self._make_auth()

        resp = AsyncMock()
        resp.status = 401
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)

        result = asyncio.run(auth.authenticate(mock_session))

        assert result is False
        assert auth.token is None

    def test_authenticate_missing_subscription_token(self):
        auth = self._make_auth()

        resp = AsyncMock()
        resp.status = 200
        resp.json = AsyncMock(return_value={"data": {}})  # subscriptionToken 없음
        resp.__aenter__ = AsyncMock(return_value=resp)
        resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=resp)

        result = asyncio.run(auth.authenticate(mock_session))

        assert result is False

    def test_authenticate_step2_http_error(self):
        auth = self._make_auth()

        step1_resp = AsyncMock()
        step1_resp.status = 200
        step1_resp.json = AsyncMock(return_value={"subscriptionToken": "tok"})
        step1_resp.__aenter__ = AsyncMock(return_value=step1_resp)
        step1_resp.__aexit__ = AsyncMock(return_value=False)

        step2_resp = AsyncMock()
        step2_resp.status = 403
        step2_resp.__aenter__ = AsyncMock(return_value=step2_resp)
        step2_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=[step1_resp, step2_resp])

        result = asyncio.run(auth.authenticate(mock_session))

        assert result is False
        assert auth.token is None

    def test_authenticate_network_exception(self):
        auth = self._make_auth()

        mock_session = MagicMock()
        mock_session.post = MagicMock(side_effect=Exception("connection refused"))

        result = asyncio.run(auth.authenticate(mock_session))

        assert result is False


# ── _fetch_driver_channels ───────────────────────────────────────────────

class TestFetchDriverChannels:
    def _make_transcriber_with_token(self):
        t = RadioTranscriber.__new__(RadioTranscriber)
        t._channel_map = {}
        t._channel_map_ts = 0.0
        t._auth = MagicMock()
        t._auth.token = "valid_token"
        return t

    def _obc_container(self, driver_num: str, content_id: str) -> dict:
        return {
            "metadata": {"contentId": content_id},
            "properties": [
                {"driverNumber": driver_num, "channelType": "OBC"},
            ],
        }

    def test_returns_obc_channels(self):
        t = self._make_transcriber_with_token()

        api_resp = AsyncMock()
        api_resp.status = 200
        api_resp.json = AsyncMock(return_value={
            "resultObj": {
                "containers": [
                    self._obc_container("1", "9001"),
                    self._obc_container("44", "9044"),
                ]
            }
        })
        api_resp.__aenter__ = AsyncMock(return_value=api_resp)
        api_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=api_resp)

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        assert result == {"1": "9001", "44": "9044"}

    def test_skips_non_obc_channels(self):
        t = self._make_transcriber_with_token()

        api_resp = AsyncMock()
        api_resp.status = 200
        api_resp.json = AsyncMock(return_value={
            "resultObj": {
                "containers": [
                    {
                        "metadata": {"contentId": "9001"},
                        "properties": [{"driverNumber": "1", "channelType": "tracker"}],
                    }
                ]
            }
        })
        api_resp.__aenter__ = AsyncMock(return_value=api_resp)
        api_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=api_resp)

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        assert result == {}

    def test_uses_cache_within_ttl(self):
        t = self._make_transcriber_with_token()
        t._channel_map = {"1": "9001"}
        t._channel_map_ts = time.time()  # 방금 갱신

        mock_session = MagicMock()

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        assert result == {"1": "9001"}
        mock_session.get.assert_not_called()  # API 호출 없어야 함

    def test_refreshes_cache_when_expired(self):
        t = self._make_transcriber_with_token()
        t._channel_map = {"1": "9001"}
        t._channel_map_ts = time.time() - 400  # TTL(300s) 초과

        api_resp = AsyncMock()
        api_resp.status = 200
        api_resp.json = AsyncMock(return_value={
            "resultObj": {
                "containers": [self._obc_container("33", "9033")]
            }
        })
        api_resp.__aenter__ = AsyncMock(return_value=api_resp)
        api_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=api_resp)

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        assert result == {"33": "9033"}
        mock_session.get.assert_called_once()

    def test_returns_existing_map_when_no_token(self):
        t = self._make_transcriber_with_token()
        t._auth.token = None
        t._channel_map = {"1": "9001"}

        mock_session = MagicMock()

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        assert result == {"1": "9001"}
        mock_session.get.assert_not_called()

    def test_handles_http_error_gracefully(self):
        t = self._make_transcriber_with_token()
        t._channel_map = {"1": "9001"}  # 기존 캐시

        api_resp = AsyncMock()
        api_resp.status = 500
        api_resp.__aenter__ = AsyncMock(return_value=api_resp)
        api_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=api_resp)

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        # 오류 시 기존 캐시 유지
        assert result == {"1": "9001"}

    def test_handles_network_exception(self):
        t = self._make_transcriber_with_token()

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=Exception("timeout"))

        result = asyncio.run(t._fetch_driver_channels(mock_session))

        assert result == {}
