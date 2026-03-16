"""
F1 라이브 상태 공유 모듈

f1_signalr.py 가 업데이트, telemetry.py 와 main.py 가 읽는 공유 인메모리 상태.
순환 임포트를 피하기 위해 별도 모듈로 분리.
"""

import asyncio
from collections import deque
from typing import Any

# ── 공유 상태 ───────────────────────────────────────────────────────────
live_state: dict[str, Any] = {
    "active":       False,   # 활성 세션 여부
    "session":      None,    # 세션 메타데이터 dict
    "drivers":      {},      # racing_number str → driver dict
    "timing":       {},      # racing_number str → timing dict
    "timing_app":   {},      # racing_number str → tyre/stint dict
    "car_data":     {},      # racing_number str → deque(maxlen=30)
    "race_control": deque(maxlen=50),   # RC 메시지 deque
    "weather":      None,    # 날씨 dict
    "team_radio":   deque(maxlen=50),   # 팀 라디오 전사 결과 deque (Step 3)
}

live_lock = asyncio.Lock()


# ── 유틸리티 ─────────────────────────────────────────────────────────────

def deep_merge(base: dict, update: dict) -> dict:
    """SignalR 부분 업데이트(diff)를 기존 상태에 딥 머지.

    - update의 값이 dict이고 base에도 같은 키의 dict가 있으면 재귀적으로 머지.
    - 그 외에는 base[k]를 update[k]로 덮어씀.
    - base를 직접 수정하고 반환함.
    """
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            deep_merge(base[k], v)
        else:
            base[k] = v
    return base


# ── 헬퍼 ────────────────────────────────────────────────────────────────

def get_active() -> bool:
    return live_state["active"]


def fmt_lap(ms_or_str) -> str:
    """밀리초(int) 또는 'MM:SS.mmm' 문자열 → '1:23.456' 형식."""
    if ms_or_str is None:
        return "-"
    if isinstance(ms_or_str, str):
        return ms_or_str if ms_or_str else "-"
    try:
        s = float(ms_or_str) / 1000.0
        mins = int(s // 60)
        secs = s % 60
        return f"{mins}:{secs:06.3f}"
    except (ValueError, TypeError):
        return str(ms_or_str)


def build_overview_drivers() -> list[dict]:
    """live_state를 읽어 telemetry.html 이 기대하는 drivers 배열로 변환."""
    drivers   = live_state["drivers"]
    timing    = live_state["timing"]
    timing_app = live_state["timing_app"]

    merged = []
    for num, info in drivers.items():
        t  = timing.get(num, {})
        ta = timing_app.get(num, {})

        # 타이어 정보 (가장 최근 stint)
        stints = ta.get("Stints", {})
        last_stint = {}
        if stints:
            last_key = max(stints.keys(), key=lambda k: int(k) if k.isdigit() else 0)
            last_stint = stints[last_key]

        compound   = last_stint.get("Compound", "-")
        total_laps = last_stint.get("TotalLaps", 0)
        start_laps = last_stint.get("StartLaps", 0)
        tyre_age   = max(0, total_laps - start_laps)

        # 피트 횟수 (NumberOfPitStops in TimingData)
        pit_count  = t.get("NumberOfPitStops", 0)

        # 갭/인터벌
        gap_to_leader = t.get("GapToLeader", "-")
        interval      = t.get("IntervalToPositionAhead", {})
        if isinstance(interval, dict):
            interval = interval.get("Value", "-")

        # 랩타임
        last_lap_raw  = t.get("LastLapTime", {})
        if isinstance(last_lap_raw, dict):
            last_lap = last_lap_raw.get("Value", "-")
        else:
            last_lap = str(last_lap_raw) if last_lap_raw else "-"

        best_lap_raw  = t.get("BestLapTime", {})
        if isinstance(best_lap_raw, dict):
            best_lap = best_lap_raw.get("Value", "-")
        else:
            best_lap = str(best_lap_raw) if best_lap_raw else "-"

        merged.append({
            "driver_number": int(num) if num.isdigit() else num,
            "name_acronym":  info.get("Tla", "???"),
            "full_name":     info.get("FullName", ""),
            "team_name":     info.get("TeamName", ""),
            "team_colour":   info.get("TeamColour", "555555"),
            "position":      int(t["Position"]) if t.get("Position", "").isdigit() else None,
            "gap_to_leader": gap_to_leader,
            "interval":      interval,
            "last_lap":      last_lap,
            "best_lap":      best_lap,
            "tyre_compound": compound,
            "tyre_laps":     total_laps,
            "tyre_age":      tyre_age,
            "pit_count":     pit_count,
        })

    merged.sort(key=lambda d: (d["position"] is None, d["position"] or 99))
    return merged


def build_car_data(driver_number: int) -> dict:
    """live_state car_data → telemetry.html 형식."""
    num     = str(driver_number)
    history_dq = live_state["car_data"].get(num, deque())
    history    = list(history_dq)

    latest = history[-1] if history else {}
    return {
        "driver_number": driver_number,
        "latest":  latest,
        "history": history,
    }


def build_race_control() -> list[dict]:
    return list(live_state["race_control"])


def build_weather() -> dict | None:
    return live_state["weather"]


def build_team_radio(limit: int = 10) -> list[dict]:
    """live_state team_radio → 최근 N개 전사 목록 반환."""
    return list(live_state["team_radio"])[-limit:]
