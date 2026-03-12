import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv
from fastapi import APIRouter

load_dotenv()

OPENF1_BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")

router = APIRouter(prefix="/api/live", tags=["telemetry"])

# ── 내부 헬퍼 ──────────────────────────────────────────────────────────

def _get(endpoint: str, params: dict = None) -> list:
    """OpenF1 API GET 요청 — 항상 list 반환, 오류 시 빈 리스트"""
    try:
        resp = requests.get(
            f"{OPENF1_BASE_URL}/{endpoint}",
            params=params or {},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _latest(records: list, key: str) -> dict:
    """driver_number=key 기준으로 가장 최근 레코드 1개 추출"""
    matches = [r for r in records if str(r.get("driver_number")) == str(key)]
    if not matches:
        return {}
    # date 필드가 있으면 최신순 정렬, 없으면 마지막 항목
    try:
        return sorted(matches, key=lambda r: r.get("date", ""), reverse=True)[0]
    except Exception:
        return matches[-1]


def _fmt_lap(seconds) -> str:
    """소수 초 → '1:23.456' 형식 변환"""
    if seconds is None:
        return "-"
    try:
        s = float(seconds)
        mins = int(s // 60)
        secs = s % 60
        return f"{mins}:{secs:06.3f}"
    except (ValueError, TypeError):
        return str(seconds)


# ── 엔드포인트 ─────────────────────────────────────────────────────────

@router.get("/session")
def get_session():
    """현재(최신) 세션 정보를 반환합니다."""
    data = _get("sessions", {"session_key": "latest"})
    if not data:
        return {"session": None, "message": "활성 세션이 없습니다."}
    s = data[-1]
    return {
        "session": {
            "session_key":      s.get("session_key"),
            "session_name":     s.get("session_name"),
            "session_type":     s.get("session_type"),
            "location":         s.get("location"),
            "country_name":     s.get("country_name"),
            "circuit_short_name": s.get("circuit_short_name"),
            "date_start":       s.get("date_start"),
            "date_end":         s.get("date_end"),
            "year":             s.get("year"),
        }
    }


@router.get("/overview")
def get_overview():
    """드라이버 순위 + 갭 + 랩타임 + 타이어 + 피트 정보를 한 번에 반환합니다."""
    # 세션 키 먼저 조회
    sessions = _get("sessions", {"session_key": "latest"})
    if not sessions:
        return {"session": None, "drivers": [], "message": "활성 세션이 없습니다."}

    session = sessions[-1]
    sk = session.get("session_key")

    # 5개 소스 병렬 호출
    sources = {
        "drivers":   ("drivers",   {"session_key": sk}),
        "intervals": ("intervals", {"session_key": sk}),
        "laps":      ("laps",      {"session_key": sk}),
        "stints":    ("stints",    {"session_key": sk}),
        "pit":       ("pit",       {"session_key": sk}),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_get, endpoint, params): name
            for name, (endpoint, params) in sources.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result(timeout=10)
            except Exception:
                results[name] = []

    drivers_raw   = results.get("drivers", [])
    intervals_raw = results.get("intervals", [])
    laps_raw      = results.get("laps", [])
    stints_raw    = results.get("stints", [])
    pit_raw       = results.get("pit", [])

    if not drivers_raw:
        return {
            "session": session,
            "drivers": [],
            "message": "드라이버 데이터가 없습니다. 세션이 아직 시작되지 않았을 수 있습니다.",
        }

    # 드라이버 번호 목록 (중복 제거)
    driver_numbers = list({str(d.get("driver_number")) for d in drivers_raw})

    # 드라이버 기본 정보 — 동일 번호 중 첫 번째
    driver_info = {}
    for d in drivers_raw:
        dn = str(d.get("driver_number"))
        if dn not in driver_info:
            driver_info[dn] = d

    # 피트 횟수 집계
    pit_counts: dict[str, int] = {}
    for p in pit_raw:
        dn = str(p.get("driver_number"))
        pit_counts[dn] = pit_counts.get(dn, 0) + 1

    # 랩 최고 기록 집계
    best_laps: dict[str, float] = {}
    for lap in laps_raw:
        dn = str(lap.get("driver_number"))
        dur = lap.get("lap_duration")
        if dur is None:
            continue
        try:
            dur_f = float(dur)
            if dn not in best_laps or dur_f < best_laps[dn]:
                best_laps[dn] = dur_f
        except (ValueError, TypeError):
            pass

    # 드라이버별 데이터 병합
    merged = []
    for dn in driver_numbers:
        info     = driver_info.get(dn, {})
        interval = _latest(intervals_raw, dn)
        last_lap = _latest(laps_raw, dn)
        stint    = _latest(stints_raw, dn)

        last_dur = last_lap.get("lap_duration")
        best_dur = best_laps.get(dn)

        merged.append({
            "driver_number":   int(dn) if dn.isdigit() else dn,
            "name_acronym":    info.get("name_acronym", "???"),
            "full_name":       info.get("full_name", ""),
            "team_name":       info.get("team_name", ""),
            "team_colour":     info.get("team_colour", "555555"),
            "position":        interval.get("position"),
            "gap_to_leader":   interval.get("gap_to_leader", "-"),
            "interval":        interval.get("interval", "-"),
            "last_lap":        _fmt_lap(last_dur),
            "best_lap":        _fmt_lap(best_dur),
            "tyre_compound":   stint.get("compound", "-"),
            "tyre_laps":       stint.get("lap_number", "-"),  # stint 시작 랩
            "tyre_age":        max(0, last_lap.get("lap_number", 0) - stint.get("lap_number", 0)) if stint else 0,
            "pit_count":       pit_counts.get(dn, 0),
        })

    # position 기준 정렬 (None은 뒤로)
    merged.sort(key=lambda d: (d["position"] is None, d["position"] or 99))

    return {
        "session": {
            "session_key":        session.get("session_key"),
            "session_name":       session.get("session_name"),
            "session_type":       session.get("session_type"),
            "location":           session.get("location"),
            "country_name":       session.get("country_name"),
            "circuit_short_name": session.get("circuit_short_name"),
            "year":               session.get("year"),
        },
        "drivers": merged,
    }


@router.get("/race-control")
def get_race_control():
    """최근 레이스 컨트롤 메시지(깃발, 세이프티카, 페널티 등)를 반환합니다."""
    data = _get("race_control", {"session_key": "latest"})
    if not data:
        return {"messages": [], "message": "레이스 컨트롤 데이터가 없습니다."}

    # 최신 30개, 시간 역순
    sorted_data = sorted(data, key=lambda r: r.get("date", ""), reverse=True)[:30]

    messages = []
    for m in sorted_data:
        messages.append({
            "date":       m.get("date"),
            "lap_number": m.get("lap_number"),
            "category":   m.get("category"),
            "flag":       m.get("flag"),
            "message":    m.get("message"),
            "scope":      m.get("scope"),
            "sector":     m.get("sector"),
            "driver_number": m.get("driver_number"),
        })

    return {"messages": messages}


@router.get("/weather")
def get_weather():
    """현재 날씨 정보를 반환합니다."""
    data = _get("weather", {"session_key": "latest"})
    if not data:
        return {"weather": None, "message": "날씨 데이터가 없습니다."}

    latest = sorted(data, key=lambda r: r.get("date", ""), reverse=True)[0]
    return {
        "weather": {
            "date":              latest.get("date"),
            "track_temperature": latest.get("track_temperature"),
            "air_temperature":   latest.get("air_temperature"),
            "humidity":          latest.get("humidity"),
            "rainfall":          latest.get("rainfall"),
            "wind_speed":        latest.get("wind_speed"),
            "wind_direction":    latest.get("wind_direction"),
            "pressure":          latest.get("pressure"),
        }
    }


@router.get("/car-data/{driver_number}")
def get_car_data(driver_number: int):
    """특정 드라이버의 최근 차량 센서 데이터(속도·스로틀·브레이크·기어·RPM·DRS)를 반환합니다."""
    data = _get("car_data", {"session_key": "latest", "driver_number": driver_number})
    if not data:
        return {"driver_number": driver_number, "data": [], "message": "차량 데이터가 없습니다."}

    # 최신 30포인트
    recent = sorted(data, key=lambda r: r.get("date", ""), reverse=True)[:30]
    recent.reverse()  # 시간순으로

    points = []
    for p in recent:
        points.append({
            "date":     p.get("date"),
            "speed":    p.get("speed"),
            "throttle": p.get("throttle"),
            "brake":    p.get("brake"),
            "drs":      p.get("drs"),
            "n_gear":   p.get("n_gear"),
            "rpm":      p.get("rpm"),
        })

    # 최신값 (마지막 포인트)
    latest = points[-1] if points else {}

    return {
        "driver_number": driver_number,
        "latest": latest,
        "history": points,
    }
