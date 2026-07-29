"""
F1 Live Telemetry — FastAPI 라우터

live_state.py 의 인메모리 상태를 읽어 프론트엔드에 반환.
상태는 main.py 에서 기동하는 F1SignalRClient 백그라운드 태스크가 채운다.
"""

import os
from collections import deque

from fastapi import APIRouter, HTTPException
import live_state as ls

router = APIRouter(prefix="/api/live", tags=["telemetry"])


# ── 엔드포인트 ─────────────────────────────────────────────────────────

@router.get("/session")
def get_session():
    """현재 세션 정보를 반환합니다."""
    if not ls.live_state["active"] or not ls.live_state["session"]:
        return {"session": None, "message": "활성 세션이 없습니다."}
    return {"session": ls.live_state["session"]}


@router.get("/overview")
def get_overview():
    """드라이버 순위 + 갭 + 랩타임 + 타이어 + 피트 정보를 한 번에 반환합니다."""
    if not ls.live_state["active"] or not ls.live_state["session"]:
        return {"session": None, "drivers": [], "message": "활성 세션이 없습니다."}

    drivers = ls.build_overview_drivers()
    return {
        "session": ls.live_state["session"],
        "drivers": drivers,
    }


@router.get("/race-control")
def get_race_control():
    """최근 레이스 컨트롤 메시지(깃발, 세이프티카, 페널티 등)를 반환합니다."""
    messages = ls.build_race_control()
    if not messages:
        return {"messages": [], "message": "레이스 컨트롤 데이터가 없습니다."}
    return {"messages": list(reversed(messages))[:30]}


@router.get("/weather")
def get_weather():
    """현재 날씨 정보를 반환합니다."""
    weather = ls.build_weather()
    if not weather:
        return {"weather": None, "message": "날씨 데이터가 없습니다."}
    return {"weather": weather}


@router.get("/car-data/{driver_number}")
def get_car_data(driver_number: int):
    """특정 드라이버의 최근 차량 센서 데이터(속도·스로틀·브레이크·기어·RPM·DRS)를 반환합니다."""
    data = ls.build_car_data(driver_number)
    if not data["history"]:
        return {"driver_number": driver_number, "data": [], "message": "차량 데이터가 없습니다."}
    return data


# ── 데모 모드 ────────────────────────────────────────────────────────────

def _require_demo_mode():
    if os.getenv("DEMO_MODE", "false").lower() != "true":
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/demo")
async def start_demo():
    """발표용 데모 데이터를 live_state에 주입합니다 (2026 바레인 GP, Lap 25/57)."""
    _require_demo_mode()
    # 2026 그리드 (번호, 약어, 이름, 팀, 팀컬러)
    _DRIVERS = [
        ("4",  "NOR", "Lando Norris",     "McLaren",      "FF8000"),
        ("81", "PIA", "Oscar Piastri",    "McLaren",      "FF8000"),
        ("16", "LEC", "Charles Leclerc",  "Ferrari",      "E8002D"),
        ("44", "HAM", "Lewis Hamilton",   "Ferrari",      "E8002D"),
        ("63", "RUS", "George Russell",   "Mercedes",     "27F4D2"),
        ("12", "ANT", "Kimi Antonelli",   "Mercedes",     "27F4D2"),
        ("1",  "VER", "Max Verstappen",   "Red Bull",     "3671C6"),
        ("6",  "HAD", "Isack Hadjar",     "Red Bull",     "3671C6"),
        ("55", "SAI", "Carlos Sainz",     "Williams",     "64C4FF"),
        ("23", "ALB", "Alexander Albon",  "Williams",     "64C4FF"),
        ("14", "ALO", "Fernando Alonso",  "Aston Martin", "358C75"),
        ("18", "STR", "Lance Stroll",     "Aston Martin", "358C75"),
        ("30", "LAW", "Liam Lawson",      "Racing Bulls", "6692FF"),
        ("37", "LIN", "Arvid Lindblad",   "Racing Bulls", "6692FF"),
        ("31", "OCO", "Esteban Ocon",     "Haas",         "B6BABD"),
        ("50", "BEA", "Oliver Bearman",   "Haas",         "B6BABD"),
        ("27", "HUL", "Nico Hülkenberg",  "Audi",         "D2FA02"),
        ("5",  "BOR", "Gabriel Bortoleto","Audi",         "D2FA02"),
        ("10", "GAS", "Pierre Gasly",     "Alpine",       "0090FF"),
        ("43", "COL", "Franco Colapinto", "Alpine",       "0090FF"),
    ]

    # 순위별 (갭, 최근랩, 최고랩, 컴파운드, 총랩, 시작랩, 피트수)
    _GRID = [
        ("",          "1:31.482", "1:31.482", "MEDIUM", 15,  0,  1),
        ("+2.841",    "1:31.654", "1:31.509", "MEDIUM", 15,  0,  1),
        ("+5.123",    "1:31.879", "1:31.712", "HARD",    8,  0,  1),
        ("+8.456",    "1:32.011", "1:31.891", "HARD",    8,  0,  1),
        ("+12.334",   "1:32.187", "1:32.013", "MEDIUM", 15,  0,  1),
        ("+15.762",   "1:32.398", "1:32.201", "MEDIUM", 12,  0,  1),
        ("+19.445",   "1:32.611", "1:32.445", "HARD",    8,  0,  1),
        ("+24.112",   "1:32.899", "1:32.677", "HARD",    8,  0,  1),
        ("+28.765",   "1:33.121", "1:32.991", "SOFT",    5, 20,  2),
        ("+33.220",   "1:33.345", "1:33.102", "SOFT",    5, 20,  2),
        ("+38.891",   "1:33.578", "1:33.401", "MEDIUM", 18,  7,  1),
        ("+42.334",   "1:33.812", "1:33.601", "MEDIUM", 18,  7,  1),
        ("+47.015",   "1:34.021", "1:33.789", "HARD",   12,  0,  1),
        ("+51.678",   "1:34.289", "1:34.011", "HARD",   12,  0,  1),
        ("+56.123",   "1:34.512", "1:34.221", "MEDIUM", 10,  0,  1),
        ("+1:01.001", "1:34.789", "1:34.512", "MEDIUM", 10,  0,  1),
        ("+1:05.234", "1:35.012", "1:34.778", "HARD",   18,  0,  1),
        ("+1:08.445", "1:35.298", "1:35.011", "HARD",   18,  0,  1),
        ("+1:13.112", "1:35.589", "1:35.234", "MEDIUM",  8,  0,  1),
        ("+1:17.890", "1:35.912", "1:35.556", "MEDIUM",  8,  0,  1),
    ]

    async with ls.live_lock:
        ls.live_state["active"] = True
        ls.live_state["session"] = {
            "session_name":      "Race",
            "location":          "Sakhir",
            "country_name":      "Bahrain",
            "circuit_short_name":"BHR",
            "year":              2026,
            "meeting_name":      "2026 Bahrain Grand Prix",
            "TotalLaps":         57,
            "CurrentLap":        25,
        }

        ls.live_state["drivers"]    = {}
        ls.live_state["timing"]     = {}
        ls.live_state["timing_app"] = {}

        for i, (num, tla, full_name, team, colour) in enumerate(_DRIVERS):
            gap, last, best, cpd, total, start, pits = _GRID[i]
            pos = i + 1

            ls.live_state["drivers"][num] = {
                "Tla": tla, "FullName": full_name,
                "TeamName": team, "TeamColour": colour,
            }
            ls.live_state["timing"][num] = {
                "Position":                   str(pos),
                "GapToLeader":                gap,
                "IntervalToPositionAhead":    {"Value": gap},
                "LastLapTime":                {"Value": last},
                "BestLapTime":                {"Value": best},
                "NumberOfPitStops":           pits,
            }
            ls.live_state["timing_app"][num] = {
                "Stints": {"0": {"Compound": cpd, "TotalLaps": total, "StartLaps": start}}
            }

        # 선두 드라이버(NOR) 차량 데이터
        ls.live_state["car_data"]["4"] = deque(
            [{"speed": 312, "throttle": 98, "brake": 0, "n_gear": 8, "rpm": 12100, "drs": 12}] * 30,
            maxlen=30,
        )

        ls.live_state["weather"] = {
            "track_temperature": 48.2,
            "air_temperature":   32.5,
            "humidity":          38.0,
            "wind_speed":        3.2,
            "rainfall":          0.0,
        }

        ls.live_state["race_control"] = deque([
            {"lap_number": 25, "date": "2026-03-01T17:23:01Z", "category": "Flag",     "flag": "GREEN",  "message": "GREEN FLAG — RACE CONTINUES"},
            {"lap_number": 22, "date": "2026-03-01T17:15:34Z", "category": "SafetyCar","flag": "",       "message": "SAFETY CAR IN THIS LAP"},
            {"lap_number": 18, "date": "2026-03-01T17:01:12Z", "category": "Flag",     "flag": "YELLOW", "message": "YELLOW FLAG SECTOR 2 — DEBRIS ON TRACK"},
            {"lap_number": 12, "date": "2026-03-01T16:42:55Z", "category": "Other",    "flag": "",       "message": "DRS ENABLED"},
            {"lap_number":  1, "date": "2026-03-01T16:00:00Z", "category": "Flag",     "flag": "GREEN",  "message": "LIGHTS OUT — RACE STARTED"},
        ], maxlen=50)

    return {"status": "ok", "message": "데모 시작: 2026 Bahrain GP Lap 25/57"}


@router.post("/demo/stop")
async def stop_demo():
    """데모 모드를 종료하고 live_state를 초기화합니다."""
    _require_demo_mode()
    async with ls.live_lock:
        ls.live_state["active"]      = False
        ls.live_state["session"]     = None
        ls.live_state["drivers"]     = {}
        ls.live_state["timing"]      = {}
        ls.live_state["timing_app"]  = {}
        ls.live_state["car_data"]    = {}
        ls.live_state["race_control"]= deque(maxlen=50)
        ls.live_state["team_radio"]  = deque(maxlen=50)
        ls.live_state["weather"]     = None

    return {"status": "ok", "message": "데모 종료"}
