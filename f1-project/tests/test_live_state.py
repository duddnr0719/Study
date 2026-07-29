"""live_state 모듈 단위 테스트

실행:
  cd "F1 project"
  python -m pytest tests/ -v
"""

import sys
import os
from collections import deque

# live_state.py를 직접 import 할 수 있도록 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import live_state as ls


# ── deep_merge ──────────────────────────────────────────────────────────

class TestDeepMerge:
    def test_flat_overwrite(self):
        """최상위 키 덮어쓰기."""
        base = {"a": 1, "b": 2}
        ls.deep_merge(base, {"b": 99, "c": 3})
        assert base == {"a": 1, "b": 99, "c": 3}

    def test_nested_merge(self):
        """중첩 dict는 재귀적으로 머지."""
        base   = {"x": {"a": 1, "b": 2}}
        update = {"x": {"b": 99, "c": 3}}
        ls.deep_merge(base, update)
        assert base == {"x": {"a": 1, "b": 99, "c": 3}}

    def test_deeply_nested(self):
        """3단계 이상 중첩."""
        base   = {"a": {"b": {"c": 1, "d": 2}}}
        update = {"a": {"b": {"d": 99, "e": 3}}}
        ls.deep_merge(base, update)
        assert base == {"a": {"b": {"c": 1, "d": 99, "e": 3}}}

    def test_dict_replaces_non_dict(self):
        """base가 비-dict인데 update가 dict이면 덮어씀."""
        base   = {"a": "string"}
        update = {"a": {"nested": True}}
        ls.deep_merge(base, update)
        assert base == {"a": {"nested": True}}

    def test_non_dict_replaces_dict(self):
        """base가 dict인데 update가 비-dict이면 덮어씀."""
        base   = {"a": {"nested": True}}
        update = {"a": "string"}
        ls.deep_merge(base, update)
        assert base == {"a": "string"}

    def test_empty_update(self):
        """빈 update — base 변경 없음."""
        base = {"a": 1}
        ls.deep_merge(base, {})
        assert base == {"a": 1}

    def test_empty_base(self):
        """빈 base — update 값 그대로 복사."""
        base   = {}
        update = {"a": 1, "b": {"c": 2}}
        ls.deep_merge(base, update)
        assert base == {"a": 1, "b": {"c": 2}}

    def test_none_value(self):
        """None 값도 그대로 할당."""
        base   = {"a": 1}
        update = {"a": None}
        ls.deep_merge(base, update)
        assert base["a"] is None

    def test_returns_base(self):
        """반환값이 base 자신이어야 함."""
        base   = {"a": 1}
        result = ls.deep_merge(base, {"b": 2})
        assert result is base

    def test_list_value_replaced(self):
        """list는 dict가 아니므로 통째로 교체."""
        base   = {"items": [1, 2, 3]}
        update = {"items": [4, 5]}
        ls.deep_merge(base, update)
        assert base["items"] == [4, 5]

    def test_signalr_timing_diff(self):
        """TimingData SignalR diff 패턴 시뮬레이션."""
        base = {
            "1": {"Position": "1", "GapToLeader": "0", "LastLapTime": {"Value": "1:20.000"}},
            "2": {"Position": "2", "GapToLeader": "+0.5"},
        }
        diff = {
            "1": {"LastLapTime": {"Value": "1:19.800"}},
        }
        ls.deep_merge(base, diff)
        assert base["1"]["LastLapTime"]["Value"] == "1:19.800"
        assert base["1"]["Position"] == "1"   # 기존 값 유지
        assert base["2"]["Position"] == "2"   # 다른 드라이버 영향 없음


# ── fmt_lap ─────────────────────────────────────────────────────────────

class TestFmtLap:
    def test_none_returns_dash(self):
        assert ls.fmt_lap(None) == "-"

    def test_empty_string_returns_dash(self):
        assert ls.fmt_lap("") == "-"

    def test_string_passthrough(self):
        assert ls.fmt_lap("1:23.456") == "1:23.456"

    def test_milliseconds_int(self):
        """83456ms → 1:23.456"""
        result = ls.fmt_lap(83456)
        assert result == "1:23.456"

    def test_zero_ms(self):
        result = ls.fmt_lap(0)
        assert result == "0:00.000"

    def test_invalid_type(self):
        """변환 불가 타입은 str()로 반환."""
        result = ls.fmt_lap([1, 2])
        assert isinstance(result, str)


# ── build_car_data ───────────────────────────────────────────────────────

class TestBuildCarData:
    def setup_method(self):
        """각 테스트 전에 live_state 초기화."""
        ls.live_state["car_data"] = {}
        ls.live_state["drivers"]  = {}
        ls.live_state["timing"]   = {}
        ls.live_state["timing_app"] = {}
        ls.live_state["race_control"] = deque(maxlen=50)
        ls.live_state["weather"]  = None
        ls.live_state["team_radio"] = deque(maxlen=50)

    def test_unknown_driver_returns_empty(self):
        result = ls.build_car_data(99)
        assert result["driver_number"] == 99
        assert result["latest"] == {}
        assert result["history"] == []

    def test_known_driver_latest(self):
        point = {"utc": "T", "speed": 300, "rpm": 12000, "gear": 8,
                 "brake": 0, "throttle": 100, "drs": 1}
        ls.live_state["car_data"]["1"] = deque([point], maxlen=30)
        result = ls.build_car_data(1)
        assert result["latest"]["speed"] == 300
        assert len(result["history"]) == 1

    def test_history_order_preserved(self):
        points = [{"speed": i} for i in range(5)]
        ls.live_state["car_data"]["44"] = deque(points, maxlen=30)
        result = ls.build_car_data(44)
        assert [p["speed"] for p in result["history"]] == [0, 1, 2, 3, 4]


# ── build_team_radio ─────────────────────────────────────────────────────

class TestBuildTeamRadio:
    def setup_method(self):
        ls.live_state["team_radio"] = deque(maxlen=50)

    def test_empty(self):
        assert ls.build_team_radio() == []

    def test_returns_recent_limit(self):
        for i in range(20):
            ls.live_state["team_radio"].append({"utc": f"T{i}", "driver": "1", "text": f"msg{i}"})
        result = ls.build_team_radio(limit=10)
        assert len(result) == 10
        assert result[-1]["text"] == "msg19"

    def test_returns_all_when_fewer_than_limit(self):
        ls.live_state["team_radio"].append({"utc": "T0", "driver": "1", "text": "hello"})
        result = ls.build_team_radio(limit=10)
        assert len(result) == 1


# ── build_race_control ───────────────────────────────────────────────────

class TestBuildRaceControl:
    def setup_method(self):
        ls.live_state["race_control"] = deque(maxlen=50)

    def test_empty(self):
        assert ls.build_race_control() == []

    def test_returns_list(self):
        msg = {"utc": "T", "lap": 5, "flag": "YELLOW", "message": "Debris", "driver": ""}
        ls.live_state["race_control"].append(msg)
        result = ls.build_race_control()
        assert isinstance(result, list)
        assert result[0]["flag"] == "YELLOW"
