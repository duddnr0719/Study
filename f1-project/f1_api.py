import os
import re
import functools
import requests
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

JOLPICA_BASE_URL = os.getenv("JOLPICA_BASE_URL", "https://api.jolpi.ca/ergast/f1")
OPENF1_BASE_URL  = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")


class JolpicaF1Client:
    """Jolpica F1 API 클라이언트 - Ergast 호환 엔드포인트"""
    def __init__(self):
        self.base_url = JOLPICA_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str) -> dict:
        url = f"{self.base_url}/{path}.json"
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json().get("MRData", {})
        except requests.RequestException as e:
            return {"error": str(e)}


# ── LRU 캐시 (동일한 경로 재요청 방지) ───────────────────────────────
@functools.lru_cache(maxsize=256)
def _cached_f1_get(path: str) -> dict:
    """캐시된 Jolpica API GET 요청 (서버 재시작 전까지 유지)"""
    client = JolpicaF1Client()
    return client._get(path)


def _validate_season(season: str) -> str | None:
    if season in ("current", "last"):
        return None
    if re.fullmatch(r"19\d{2}|20\d{2}", season):
        return None
    return f"'{season}'은 유효하지 않은 시즌 값입니다. 연도(예: '2024') 또는 'current'를 사용하세요."


def _validate_round(round_num: str) -> str | None:
    if round_num in ("last", "next"):
        return None
    if re.fullmatch(r"\d{1,2}", round_num):
        return None
    return f"'{round_num}'은 유효하지 않은 라운드 값입니다. 숫자(예: '1', '5') 또는 'last'를 사용하세요."


# ── 기존 도구 ─────────────────────────────────────────────────────────

@tool
def get_driver_standings(season: str = "current") -> str:
    """F1 드라이버 챔피언십 스탠딩(순위)을 조회합니다.
    season: 연도(예: '2024', '2023') 또는 'current'.
    프리시즌/테스트 데이터는 지원하지 않습니다."""
    err = _validate_season(season)
    if err:
        return err
    data = _cached_f1_get(f"{season}/driverstandings")
    if "error" in data:
        return f"API 조회 실패: {data['error']}. 웹 검색을 사용하세요."
    standings_lists = data.get("StandingsTable", {}).get("StandingsLists", [])
    if not standings_lists:
        return f"[{season}] 드라이버 스탠딩 데이터 없음. 웹 검색을 사용하세요."
    standings = standings_lists[0].get("DriverStandings", [])
    lines = [f"### {season} 드라이버 챔피언십 스탠딩\n"]
    lines.append("| 순위 | 드라이버 | 팀 | 포인트 | 우승 |")
    lines.append("|------|---------|-----|--------|------|")
    for s in standings[:20]:
        driver = s["Driver"]
        constructor = s["Constructors"][0]["name"] if s["Constructors"] else "N/A"
        wins = s.get("wins", "0")
        lines.append(f"| {s['position']} | {driver['givenName']} {driver['familyName']} | {constructor} | {s['points']} | {wins} |")
    return "\n".join(lines)


@tool
def get_constructor_standings(season: str = "current") -> str:
    """F1 컨스트럭터(팀) 챔피언십 스탠딩(순위)을 조회합니다.
    season: 연도(예: '2024', '2023') 또는 'current'."""
    err = _validate_season(season)
    if err:
        return err
    data = _cached_f1_get(f"{season}/constructorstandings")
    if "error" in data:
        return f"API 조회 실패: {data['error']}. 웹 검색을 사용하세요."
    standings_lists = data.get("StandingsTable", {}).get("StandingsLists", [])
    if not standings_lists:
        return f"[{season}] 컨스트럭터 스탠딩 데이터 없음. 웹 검색을 사용하세요."
    standings = standings_lists[0].get("ConstructorStandings", [])
    lines = [f"### {season} 컨스트럭터 챔피언십 스탠딩\n"]
    lines.append("| 순위 | 팀 | 포인트 | 우승 |")
    lines.append("|------|-----|--------|------|")
    for s in standings:
        wins = s.get("wins", "0")
        lines.append(f"| {s['position']} | {s['Constructor']['name']} | {s['points']} | {wins} |")
    return "\n".join(lines)


@tool
def get_race_results(season: str = "current", round_num: str = "last") -> str:
    """특정 시즌과 라운드의 F1 레이스 결과를 조회합니다.
    season: 연도(예: '2024') 또는 'current'.
    round_num: 숫자(예: '1', '5') 또는 'last'.
    프리시즌 테스트, 스프린트 등 공식 레이스가 아닌 경우 조회 불가."""
    err = _validate_season(season) or _validate_round(round_num)
    if err:
        return err
    data = _cached_f1_get(f"{season}/{round_num}/results")
    if "error" in data:
        return f"API 조회 실패: {data['error']}. 웹 검색을 사용하세요."
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return f"[{season} Round {round_num}] 레이스 결과 없음. 웹 검색을 사용하세요."
    race = races[0]
    lines = [f"### {race['raceName']} ({race['date']}) 결과\n"]
    lines.append("| 순위 | 드라이버 | 팀 | 기록 | 포인트 |")
    lines.append("|------|---------|-----|------|--------|")
    for r in race.get("Results", [])[:20]:
        driver = r["Driver"]
        time_str = r.get("Time", {}).get("time", r.get("status", "N/A"))
        points = r.get("points", "0")
        lines.append(f"| {r['position']} | {driver['givenName']} {driver['familyName']} | {r['Constructor']['name']} | {time_str} | {points} |")
    return "\n".join(lines)


@tool
def get_live_telemetry(session_key: str = "latest") -> str:
    """OpenF1 API를 통해 실시간 또는 최근 세션 정보를 조회합니다.
    데이터가 없으면 웹 검색 툴을 사용하세요."""
    url = f"{OPENF1_BASE_URL}/sessions"
    try:
        resp = requests.get(url, params={"session_key": session_key}, timeout=5)
        data = resp.json()
        if not data:
            return "실시간 세션 데이터가 없습니다. 웹 검색을 사용하세요."
        s = data[0]
        return (
            f"**현재 세션:** {s['session_name']} ({s['location']})\n"
            f"**날짜:** {s['date_start']}\n**유형:** {s['session_type']}"
        )
    except Exception as e:
        return f"실시간 데이터 조회 실패: {str(e)}. 웹 검색을 사용하세요."


# ── 신규 도구 ─────────────────────────────────────────────────────────

@tool
def get_qualifying_results(season: str = "current", round_num: str = "last") -> str:
    """특정 시즌과 라운드의 F1 예선(퀄리파이잉) 결과를 조회합니다.
    season: 연도(예: '2024') 또는 'current'.
    round_num: 숫자(예: '1', '5') 또는 'last'.
    Q1·Q2·Q3 기록을 모두 포함합니다."""
    err = _validate_season(season) or _validate_round(round_num)
    if err:
        return err
    data = _cached_f1_get(f"{season}/{round_num}/qualifying")
    if "error" in data:
        return f"API 조회 실패: {data['error']}. 웹 검색을 사용하세요."
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return f"[{season} Round {round_num}] 예선 결과 없음. 웹 검색을 사용하세요."
    race = races[0]
    lines = [f"### {race['raceName']} 예선 결과\n"]
    lines.append("| 그리드 | 드라이버 | 팀 | Q1 | Q2 | Q3 |")
    lines.append("|--------|---------|-----|-----|-----|-----|")
    for r in race.get("QualifyingResults", []):
        driver = r["Driver"]
        q1 = r.get("Q1", "-")
        q2 = r.get("Q2", "-")
        q3 = r.get("Q3", "-")
        lines.append(f"| {r['position']} | {driver['givenName']} {driver['familyName']} | {r['Constructor']['name']} | {q1} | {q2} | {q3} |")
    return "\n".join(lines)


@tool
def get_race_schedule(season: str = "current") -> str:
    """F1 시즌 레이스 캘린더(일정)를 조회합니다.
    season: 연도(예: '2025', '2026') 또는 'current'.
    각 라운드의 그랑프리명, 개최지, 날짜를 반환합니다."""
    err = _validate_season(season)
    if err:
        return err
    data = _cached_f1_get(f"{season}/races")
    if "error" in data:
        return f"API 조회 실패: {data['error']}. 웹 검색을 사용하세요."
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return f"[{season}] 레이스 일정 없음. 웹 검색을 사용하세요."
    lines = [f"### {season} F1 레이스 캘린더\n"]
    lines.append("| 라운드 | 그랑프리 | 서킷 | 국가 | 날짜 |")
    lines.append("|--------|---------|------|------|------|")
    for r in races:
        circuit = r.get("Circuit", {})
        location = circuit.get("Location", {})
        country = location.get("country", "-")
        locality = location.get("locality", "-")
        lines.append(f"| {r['round']} | {r['raceName']} | {locality} | {country} | {r['date']} |")
    return "\n".join(lines)


@tool
def get_pitstops(season: str = "current", round_num: str = "last") -> str:
    """특정 레이스의 피트스톱 데이터를 조회합니다.
    season: 연도(예: '2024') 또는 'current'.
    round_num: 숫자(예: '1', '5') 또는 'last'.
    각 드라이버의 피트스톱 랩, 횟수, 소요 시간을 반환합니다."""
    err = _validate_season(season) or _validate_round(round_num)
    if err:
        return err
    data = _cached_f1_get(f"{season}/{round_num}/pitstops")
    if "error" in data:
        return f"API 조회 실패: {data['error']}. 웹 검색을 사용하세요."
    races = data.get("RaceTable", {}).get("Races", [])
    if not races:
        return f"[{season} Round {round_num}] 피트스톱 데이터 없음. 웹 검색을 사용하세요."
    race = races[0]
    pitstops = race.get("PitStops", [])
    if not pitstops:
        return "피트스톱 데이터가 없습니다."
    lines = [f"### {race['raceName']} 피트스톱 데이터\n"]
    lines.append("| 드라이버 번호 | 스톱 횟수 | 랩 | 시간 | 소요 시간(초) |")
    lines.append("|-------------|-----------|-----|------|------------|")
    for p in pitstops:
        lines.append(f"| {p['driverId']} | {p['stop']} | {p['lap']} | {p['time']} | {p['duration']} |")
    return "\n".join(lines)


@tool
def compare_drivers(season: str, driver1_id: str, driver2_id: str) -> str:
    """두 드라이버의 시즌 성적을 비교합니다.
    season: 연도(예: '2024') 또는 'current'.
    driver1_id: 첫 번째 드라이버 ID (예: 'verstappen', 'hamilton', 'leclerc').
    driver2_id: 두 번째 드라이버 ID (예: 'norris', 'sainz', 'russell').
    드라이버 ID는 소문자 성(surname)을 사용합니다."""
    err = _validate_season(season)
    if err:
        return err

    results = {}
    for driver_id in [driver1_id, driver2_id]:
        data = _cached_f1_get(f"{season}/drivers/{driver_id}/results")
        if "error" in data:
            results[driver_id] = {"error": data["error"]}
            continue
        races = data.get("RaceTable", {}).get("Races", [])
        wins = 0
        podiums = 0
        points = 0.0
        dnfs = 0
        positions = []
        for race in races:
            for r in race.get("Results", []):
                pos = r.get("position", "0")
                status = r.get("status", "")
                pts = float(r.get("points", 0))
                points += pts
                try:
                    pos_int = int(pos)
                    positions.append(pos_int)
                    if pos_int == 1:
                        wins += 1
                    if pos_int <= 3:
                        podiums += 1
                except ValueError:
                    pass
                if "Ret" in status or "DNF" in status or "DNS" in status:
                    dnfs += 1
        avg_pos = round(sum(positions) / len(positions), 2) if positions else "-"
        results[driver_id] = {
            "races": len(races),
            "wins": wins,
            "podiums": podiums,
            "points": points,
            "dnfs": dnfs,
            "avg_finish": avg_pos,
        }

    # 결과 포매팅
    lines = [f"### {season} 드라이버 비교: {driver1_id} vs {driver2_id}\n"]
    lines.append(f"| 항목 | {driver1_id} | {driver2_id} |")
    lines.append("|------|------------|------------|")

    stats = ["races", "wins", "podiums", "points", "dnfs", "avg_finish"]
    labels = ["출전 레이스", "우승", "포디움", "포인트", "DNF", "평균 피니시"]

    for stat, label in zip(stats, labels):
        v1 = results.get(driver1_id, {}).get(stat, "N/A")
        v2 = results.get(driver2_id, {}).get(stat, "N/A")
        # 더 나은 값 강조
        try:
            better_high = stat in ["wins", "podiums", "points", "races"]
            better_low  = stat in ["dnfs", "avg_finish"]
            f1, f2 = float(v1), float(v2)
            if better_high and f1 > f2:
                v1, v2 = f"**{v1}**", str(v2)
            elif better_high and f2 > f1:
                v1, v2 = str(v1), f"**{v2}**"
            elif better_low and f1 < f2:
                v1, v2 = f"**{v1}**", str(v2)
            elif better_low and f2 < f1:
                v1, v2 = str(v1), f"**{v2}**"
        except (TypeError, ValueError):
            pass
        lines.append(f"| {label} | {v1} | {v2} |")

    return "\n".join(lines)
