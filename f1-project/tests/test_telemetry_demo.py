"""telemetry.py 데모 엔드포인트 단위 테스트

실행:
  cd "F1 project"
  python -m pytest tests/ -v
"""

import sys
import os
import asyncio
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["DEMO_MODE"] = "true"  # 데모 엔드포인트 활성화

import live_state as ls
from telemetry import start_demo, stop_demo


def run(coro):
    return asyncio.run(coro)


def reset_state():
    ls.live_state["active"]       = False
    ls.live_state["session"]      = None
    ls.live_state["drivers"]      = {}
    ls.live_state["timing"]       = {}
    ls.live_state["timing_app"]   = {}
    ls.live_state["car_data"]     = {}
    ls.live_state["race_control"] = deque(maxlen=50)
    ls.live_state["weather"]      = None
    ls.live_state["team_radio"]   = deque(maxlen=50)


# ── start_demo ───────────────────────────────────────────────────────────

class TestStartDemo:
    def setup_method(self):
        reset_state()

    def test_returns_ok(self):
        result = run(start_demo())
        assert result["status"] == "ok"

    def test_active_flag_set(self):
        run(start_demo())
        assert ls.live_state["active"] is True

    def test_session_populated(self):
        run(start_demo())
        session = ls.live_state["session"]
        assert session is not None
        assert session["year"] == 2026
        assert session["circuit_short_name"] == "BHR"
        assert session["TotalLaps"] == 57
        assert session["CurrentLap"] == 25

    def test_20_drivers_loaded(self):
        run(start_demo())
        assert len(ls.live_state["drivers"]) == 20
        assert len(ls.live_state["timing"]) == 20
        assert len(ls.live_state["timing_app"]) == 20

    def test_leader_is_norris(self):
        run(start_demo())
        nor = ls.live_state["drivers"].get("4")
        assert nor is not None
        assert nor["Tla"] == "NOR"
        assert ls.live_state["timing"]["4"]["Position"] == "1"

    def test_leader_gap_is_empty(self):
        run(start_demo())
        assert ls.live_state["timing"]["4"]["GapToLeader"] == ""

    def test_second_driver_has_gap(self):
        run(start_demo())
        assert ls.live_state["timing"]["81"]["GapToLeader"] == "+2.841"

    def test_car_data_injected_for_leader(self):
        run(start_demo())
        car = ls.live_state["car_data"].get("4")
        assert car is not None
        assert len(car) == 30
        assert car[-1]["speed"] == 312

    def test_weather_populated(self):
        run(start_demo())
        w = ls.live_state["weather"]
        assert w is not None
        assert w["rainfall"] == 0.0
        assert w["track_temperature"] == 48.2

    def test_race_control_has_messages(self):
        run(start_demo())
        msgs = list(ls.live_state["race_control"])
        assert len(msgs) == 5
        assert msgs[-1]["flag"] == "GREEN"  # 가장 최근 메시지

    def test_tyre_compound_assigned(self):
        run(start_demo())
        # NOR(4번) — MEDIUM 타이어
        stints = ls.live_state["timing_app"]["4"]["Stints"]
        assert stints["0"]["Compound"] == "MEDIUM"

    def test_pit_count_assigned(self):
        run(start_demo())
        # SAI(55번) — 2회 피트
        assert ls.live_state["timing"]["55"]["NumberOfPitStops"] == 2


# ── stop_demo ────────────────────────────────────────────────────────────

class TestStopDemo:
    def setup_method(self):
        reset_state()
        run(start_demo())  # 먼저 데모를 시작해 둠

    def test_returns_ok(self):
        result = run(stop_demo())
        assert result["status"] == "ok"

    def test_active_flag_cleared(self):
        run(stop_demo())
        assert ls.live_state["active"] is False

    def test_session_cleared(self):
        run(stop_demo())
        assert ls.live_state["session"] is None

    def test_drivers_cleared(self):
        run(stop_demo())
        assert ls.live_state["drivers"] == {}

    def test_timing_cleared(self):
        run(stop_demo())
        assert ls.live_state["timing"] == {}

    def test_car_data_cleared(self):
        run(stop_demo())
        assert ls.live_state["car_data"] == {}

    def test_weather_cleared(self):
        run(stop_demo())
        assert ls.live_state["weather"] is None

    def test_race_control_cleared(self):
        run(stop_demo())
        assert list(ls.live_state["race_control"]) == []

    def test_idempotent_double_stop(self):
        """stop을 두 번 호출해도 오류 없어야 함."""
        run(stop_demo())
        result = run(stop_demo())
        assert result["status"] == "ok"
        assert ls.live_state["active"] is False
