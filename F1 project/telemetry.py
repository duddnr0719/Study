"""
F1 Live Telemetry — FastAPI 라우터

live_state.py 의 인메모리 상태를 읽어 프론트엔드에 반환.
상태는 main.py 에서 기동하는 F1SignalRClient 백그라운드 태스크가 채운다.
"""

from fastapi import APIRouter
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
