import os
import re
import uuid
import json
import time
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from telemetry import router as telemetry_router

from langchain_ollama import ChatOllama
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

# LangGraph 버전에 따라 import 경로 분기
try:
    from langgraph.prebuilt import create_react_agent
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    from langchain.agents import create_react_agent  # type: ignore
    from langgraph.checkpoint.memory import MemorySaver

from f1_api import (
    get_driver_standings,
    get_constructor_standings,
    get_race_results,
    get_live_telemetry,
    get_qualifying_results,
    get_race_schedule,
    get_pitstops,
    compare_drivers,
)

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────────
LLM_MODEL        = os.getenv("OLLAMA_LLM_MODEL", "qwen3.5:122b")
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://100.66.16.106:11434")
EMBEDDING_MODEL  = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
CHROMA_DIR       = os.getenv("CHROMA_DIR", "./chroma_db")
OPENF1_BASE_URL  = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")
CURRENT_SEASON   = os.getenv("F1_SEASON", str(datetime.now().year))

# ── FastAPI 앱 ─────────────────────────────────────────────────────────
app = FastAPI(title="F1 Doctor Agentic AI", version="4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(telemetry_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── 도구 설정 ─────────────────────────────────────────────────────────
_ddg_wrapper = DuckDuckGoSearchAPIWrapper(region="us-en", time="m", max_results=10)
_ddg_raw     = DuckDuckGoSearchRun(api_wrapper=_ddg_wrapper)

# Tavily 초기화 — API 키 없을 시 DuckDuckGo 전용으로 폴백
try:
    _tavily     = TavilySearch(max_results=10)
    _use_tavily = True
except Exception:
    _tavily     = None
    _use_tavily = False

def _run_search(query: str) -> str:
    """쿼리에 F1 키워드 자동 추가 후 Tavily 우선 검색, 실패 시 DuckDuckGo 폴백."""
    q_lower = query.lower()
    if "f1" not in q_lower and "formula 1" not in q_lower and "formula one" not in q_lower:
        query = f"F1 Formula 1 {query}"
    if _use_tavily:
        try:
            result = _tavily.invoke({"query": query})
            if isinstance(result, list) and result:
                return "\n\n".join(
                    r.get("content", "") for r in result if r.get("content")
                )
        except Exception:
            pass
    return _ddg_raw.run(query)

@tool
def search(query: str) -> str:
    """F1 Formula 1 관련 최신 뉴스와 정보를 웹에서 검색합니다.
    쿼리는 영어로 작성하고 F1 또는 Formula 1 키워드를 포함하세요."""
    return _run_search(query)

embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
vector_db  = Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
retriever  = vector_db.as_retriever(search_kwargs={"k": 3})

@tool
def search_regulations(query: str) -> str:
    """FIA F1 공식 규정집에서 관련 조항을 검색합니다.
    2024년 통합 규정집과 2026년 섹션 A~F(일반/스포팅/기술/재정/운영) 규정집이 포함되어 있습니다.
    2026년이 최신 규정입니다. 규정 비교, 연도별 변경사항, 특정 조항 검색에 사용하세요."""
    docs = retriever.invoke(query)
    if not docs:
        return "관련 규정을 찾을 수 없습니다. duckduckgo_search를 사용해 주세요."
    results = []
    for doc in docs:
        season  = doc.metadata.get("season", "?")
        section = doc.metadata.get("section", "")
        header  = f"[{season}년 규정 / {section}]" if section else f"[{season}년 규정]"
        results.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(results)

tools = [
    get_driver_standings,
    get_constructor_standings,
    get_race_results,
    get_qualifying_results,
    get_race_schedule,
    get_pitstops,
    compare_drivers,
    get_live_telemetry,
    search_regulations,
    search
]

# ── 시스템 프롬프트 ────────────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 F1(포뮬러 원 월드 챔피언십) 전문가 AI 어시스턴트 'F1 Doctor'입니다.

============================================================
## [규칙 0] F1 전용 — 가장 먼저 적용
============================================================
- 당신은 오직 F1(포뮬러 원 월드 챔피언십)에 관한 질문만 처리합니다.
- MLB, PGA, K리그, 마라톤, 사이클, WRC, IndyCar, MotoGP 등 F1이 아닌 스포츠 질문은
  즉시 "저는 F1 전문 AI입니다. F1 관련 질문을 해주세요."로 답변하고 종료합니다.

============================================================
## [규칙 1] 질문 유형별 필수 도구 순서 (반드시 이 순서를 따르세요)
============================================================

| 질문 유형 | 1순위 (항상 먼저) | 2순위 (1순위 데이터 없을 때만) |
|---------|----------------|--------------------------|
| 시즌 일정 / 캘린더 / 다음 레이스 | `get_race_schedule(season="2026")` | duckduckgo_search |
| 레이스 결과 / 우승자 | `get_race_results(season="current", round_num="last")` | duckduckgo_search |
| 드라이버 챔피언십 순위 | `get_driver_standings(season="current")` | duckduckgo_search |
| 팀(컨스트럭터) 순위 | `get_constructor_standings(season="current")` | duckduckgo_search |
| 예선 결과 / 그리드 순서 | `get_qualifying_results(season="current", round_num="last")` | duckduckgo_search |
| 피트스톱 전략 / 타이어 | `get_pitstops(season="current", round_num="last")` | duckduckgo_search |
| 드라이버 성적 비교 | `compare_drivers(season=..., driver1_id=..., driver2_id=...)` | duckduckgo_search |
| FIA 규정 / 기술 규정 | `search_regulations(query=...)` | duckduckgo_search |
| 최신 뉴스 / 이적 / 루머 | duckduckgo_search (직접 사용) | — |
| 프리시즌 테스트 / 비공식 세션 | duckduckgo_search (직접 사용) | — |

⚠️ **duckduckgo_search는 위 표에서 2순위로 지정된 경우에만 사용합니다.**
⚠️ **"시즌 일정"을 물어보면 절대 duckduckgo_search를 먼저 사용하지 마세요. get_race_schedule을 먼저 호출하세요.**

============================================================
## [규칙 2] duckduckgo_search 사용 시 필수 쿼리 형식
============================================================
- 반드시 "F1" 또는 "Formula 1"을 쿼리 앞에 붙이세요.
  - ❌ 금지: "2026 시즌 일정", "최근 레이스 결과"
  - ✅ 필수: "F1 Formula 1 2026 race calendar schedule", "F1 Formula 1 latest Grand Prix result 2026"
- 검색 결과를 답변에 쓰기 전에 반드시 확인:
  - "Formula 1", "Grand Prix", "F1", "FIA", "constructor", "driver championship" 중 하나가 포함되어 있는가?
  - MLB, PGA, K리그, 마라톤 등 비F1 스포츠 내용이면 → 결과 무시, "F1 데이터를 찾지 못했습니다. formula1.com을 확인해 주세요." 답변

============================================================
## [규칙 3] 도구별 파라미터 제한
============================================================
- get_race_results / get_qualifying_results / get_pitstops
  - season: 연도 문자열 또는 "current" (예: "2025", "current")
  - round_num: 숫자 문자열 또는 "last" (예: "1", "23", "last")
  - ❌ "preseason", "test", "sprint" 등 비숫자 불가
- get_driver_standings / get_constructor_standings / get_race_schedule
  - season: 연도 문자열 또는 "current"
- compare_drivers
  - driver1_id / driver2_id: 소문자 성(surname) (예: "norris", "piastri", "verstappen")

============================================================
## [규칙 4] F1 지식 베이스
============================================================
### 규정 데이터베이스
- 2024년: 통합 규정집 (스포팅+기술 통합)
- 2026년: Section A(일반) / B(스포팅) / C(기술) / D(재정-팀) / E(재정-PU) / F(운영) ← 최신
- 연도 미지정 시 2026년 규정 기준으로 답변
- 2024↔2026 비교 요청 시 두 연도 모두 search_regulations로 검색

### 2026 주요 규정 변경
- 파워유닛: 새 하이브리드 규정 (전기 출력 비중 대폭 확대, MGU-H 폐지)
- 공력: 액티브 에어로다이나믹스 도입 (DRS 폐지, 이동식 전면/후면 윙 허용)
- 차체: 차폭 축소 및 중량 감소

### 2026 드라이버 라인업
| 팀 | 드라이버 |
|---|---|
| McLaren | Lando Norris (2025 WDC 🏆), Oscar Piastri |
| Ferrari | Charles Leclerc, Lewis Hamilton |
| Mercedes | George Russell, Kimi Antonelli |
| Red Bull Racing | Max Verstappen, Isack Hadjar |
| Racing Bulls | Liam Lawson, Arvid Lindblad |
| Williams | Carlos Sainz, Alex Albon |
| Aston Martin | Fernando Alonso, Lance Stroll |
| Haas | Esteban Ocon, Ollie Bearman |
| Audi | Nico Hülkenberg, Gabriel Bortoleto |
| Alpine | Pierre Gasly, Franco Colapinto |
| Cadillac (신규) | Valtteri Bottas, Sergio Perez |

주요 이적: 해밀턴 메르세데스→페라리, 안토넬리 메르세데스 데뷔, 하다르 레드불 데뷔, 카데락 신규 참가

============================================================
## [규칙 5] 답변 형식
============================================================
- 항상 한국어로 답변하세요.
- 마크다운(표, 굵은 글씨, 목록)을 적극 활용하여 가독성을 높이세요.
- 규정 답변 시 연도와 섹션 명시 (예: "2026년 Section C 기술 규정에 따르면...").
- 데이터 출처를 간략히 언급하세요.
- F1 데이터를 찾지 못한 경우, 추측 없이 "데이터를 찾지 못했습니다"로 솔직하게 답변하세요.
"""

# ── 에이전트 초기화 (MemorySaver로 대화 히스토리 유지) ─────────────────
llm = ChatOllama(model=LLM_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
checkpointer = MemorySaver()
agent_executor = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT, checkpointer=checkpointer)

# ── Request/Response 모델 ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

# ── API 데이터 유효성 검사 ─────────────────────────────────────────────
_F1_MARKERS = ['formula 1', 'grand prix', ' f1 ', 'fia', 'constructor',
               'driver', 'circuit', 'race', 'formula one', 'motorsport',
               'mclaren', 'ferrari', 'mercedes', 'red bull', 'alpine',
               'williams', 'haas', 'aston martin', 'audi', 'cadillac']

def _is_f1_content(text: str) -> bool:
    """텍스트가 F1 관련 내용인지 검증합니다."""
    return any(m in text.lower() for m in _F1_MARKERS)

# 히라가나(\u3040-\u309F) · 카타카나(\u30A0-\u30FF) 제거
_JP_PATTERN = re.compile(r'[\u3040-\u30FF]+')

def _strip_japanese(text: str) -> str:
    """LLM 출력에서 일본어(히라가나·카타카나) 문자를 제거합니다."""
    return _JP_PATTERN.sub('', text)

def _api_ok(data: str) -> bool:
    """API 반환값이 실제 데이터인지(오류 메시지가 아닌지) 확인합니다."""
    if not data:
        return False
    error_indicators = ['없음', '실패', 'error', '웹 검색을 사용하세요']
    return not any(ind in data for ind in error_indicators)


# ── 실시간 세션 컨텍스트 (30초 캐시) ──────────────────────────────────
_live_ctx_cache: dict = {"data": None, "ts": 0.0}
_LIVE_CTX_TTL = 30  # seconds

def _openf1(endpoint: str, params: dict = None) -> list:
    """OpenF1 API GET — 오류 시 빈 리스트 반환"""
    try:
        r = requests.get(f"{OPENF1_BASE_URL}/{endpoint}",
                         params=params or {}, timeout=6)
        r.raise_for_status()
        d = r.json()
        return d if isinstance(d, list) else []
    except Exception:
        return []

def _fetch_live_context() -> str | None:
    """
    OpenF1에서 최신 F1 세션 데이터를 가져와 LLM 컨텍스트 문자열로 반환합니다.
    세션이 없거나 24시간 이상 지난 경우 None 반환. 30초 캐시 적용.
    포함 데이터: 세션 정보 · 레이스 컨트롤 메시지 · 드라이버 포지션 · 날씨
    """
    global _live_ctx_cache
    now = time.time()
    if now - _live_ctx_cache["ts"] < _LIVE_CTX_TTL and _live_ctx_cache["data"] is not None:
        return _live_ctx_cache["data"]

    def _cache(val):
        _live_ctx_cache["data"] = val
        _live_ctx_cache["ts"]   = time.time()
        return val

    try:
        sessions = _openf1("sessions", {"session_key": "latest"})
        if not sessions:
            return _cache(None)

        session = sessions[-1]
        sk = session.get("session_key")

        # 24시간 이상 지난 세션은 무시
        date_start_str = session.get("date_start", "")
        if date_start_str:
            try:
                ds = datetime.fromisoformat(date_start_str.replace("Z", "+00:00"))
                hours_ago = (datetime.now(timezone.utc) - ds).total_seconds() / 3600
                if hours_ago > 24:
                    return _cache(None)
            except Exception:
                pass

        session_name = session.get("session_name", "")
        session_type = session.get("session_type", "")
        location     = session.get("location", "")
        country      = session.get("country_name", "")
        year         = session.get("year", "")

        # 병렬 호출: 레이스 컨트롤 + 인터벌 + 드라이버 + 날씨
        sources = {
            "rc":       ("race_control", {"session_key": sk}),
            "intervals":("intervals",    {"session_key": sk}),
            "drivers":  ("drivers",      {"session_key": sk}),
            "weather":  ("weather",      {"session_key": sk}),
        }
        results: dict = {}
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(_openf1, ep, p): name for name, (ep, p) in sources.items()}
            for fut in as_completed(futs):
                try:
                    results[futs[fut]] = fut.result(timeout=10)
                except Exception:
                    results[futs[fut]] = []

        rc_raw       = results.get("rc", [])
        intervals_raw= results.get("intervals", [])
        drivers_raw  = results.get("drivers", [])
        weather_raw  = results.get("weather", [])

        lines = [
            f"## F1 세션 정보",
            f"- 이벤트: {year} {country} GP — {location} / {session_name} ({session_type})",
            f"- 세션 키: {sk}",
        ]

        # ── 날씨 ──────────────────────────────────────────────────────
        if weather_raw:
            w = sorted(weather_raw, key=lambda r: r.get("date", ""), reverse=True)[0]
            rain = "🌧 비" if w.get("rainfall") else "☀ 맑음"
            lines.append(
                f"- 날씨: {rain} | 트랙 {w.get('track_temperature','?')}°C "
                f"| 기온 {w.get('air_temperature','?')}°C "
                f"| 습도 {w.get('humidity','?')}%"
            )

        # ── 레이스 컨트롤 메시지 ──────────────────────────────────────
        if rc_raw:
            rc_sorted = sorted(rc_raw, key=lambda r: r.get("date",""), reverse=True)[:25]
            rc_sorted.reverse()
            lines.append("\n### 레이스 컨트롤 메시지 (시간 순)")
            lines.append("| 랩 | 플래그 | 메시지 | 드라이버# |")
            lines.append("|-----|--------|--------|----------|")
            for m in rc_sorted:
                flag = m.get("flag") or m.get("category", "")
                lap  = m.get("lap_number", "-")
                msg  = m.get("message", "")
                dn   = m.get("driver_number", "-") or "-"
                lines.append(f"| {lap} | {flag} | {msg} | {dn} |")

        # ── 드라이버 현황 (상위 10위) ──────────────────────────────────
        if intervals_raw and drivers_raw:
            driver_map = {}
            for d in drivers_raw:
                dn = str(d.get("driver_number", ""))
                if dn and dn not in driver_map:
                    driver_map[dn] = d

            # 최신 인터벌만 추출
            latest_intervals: dict[str, dict] = {}
            for iv in intervals_raw:
                dn = str(iv.get("driver_number", ""))
                if dn:
                    prev = latest_intervals.get(dn, {})
                    if iv.get("date","") >= prev.get("date",""):
                        latest_intervals[dn] = iv

            rows = []
            for dn, iv in latest_intervals.items():
                info = driver_map.get(dn, {})
                rows.append({
                    "pos":  iv.get("position") or 99,
                    "num":  dn,
                    "acr":  info.get("name_acronym","???"),
                    "team": info.get("team_name",""),
                    "gap":  iv.get("gap_to_leader", "-"),
                    "int":  iv.get("interval", "-"),
                })
            rows.sort(key=lambda r: r["pos"])

            if rows:
                lines.append("\n### 현재 드라이버 순위")
                lines.append("| P | # | 드라이버 | 팀 | 리더 갭 | 인터벌 |")
                lines.append("|---|---|---------|-----|---------|--------|")
                for r in rows[:10]:
                    lines.append(
                        f"| {r['pos']} | {r['num']} | {r['acr']} "
                        f"| {r['team']} | {r['gap']} | {r['int']} |"
                    )

        result = "\n".join(lines)
        return _cache(result)

    except Exception:
        return _cache(None)


# ── 직접 답변 생성 (에이전트 우회) ─────────────────────────────────────
_DIRECT_PROMPT = """당신은 F1 전문가 AI 'F1 Doctor'입니다.
아래 F1 공식 데이터를 바탕으로 사용자 질문에 **한국어**로 답변하세요.
마크다운 표, 굵은 글씨, 목록을 적극 활용하세요.
데이터에 없는 내용은 추측하지 마세요.

[F1 공식 데이터]
{data}

[사용자 질문]
{question}"""

_LIVE_PROMPT = """당신은 F1 전문가 AI 'F1 Doctor'입니다.
아래는 현재(또는 가장 최근) F1 세션의 실시간 공식 데이터입니다.
이 데이터를 분석하여 사용자 질문에 **한국어**로 답변하세요.

레이스 컨트롤 메시지 해석 가이드:
- YELLOW / DOUBLE YELLOW : 황색기 — 해당 구간 위험, 추월 금지
- RED FLAG : 적기 — 세션 즉시 중단, 피트레인으로 복귀
- SAFETY CAR : 세이프티카 출동 (배포/회수)
- VIRTUAL SAFETY CAR (VSC) : 버추얼 세이프티카 — 전 구간 델타 타임 제한
- DRS DISABLED / ENABLED : DRS 사용 가능 여부
- INCIDENT / UNDER INVESTIGATION : 사건 조사 중
- TIME PENALTY / DRIVE THROUGH / STOP AND GO : 페널티 유형
- 날씨(rainfall=True) : 빗길 — 사고 위험 증가 요인

사고 원인 분석 시: 레이스 컨트롤 메시지의 시퀀스, 해당 랩 번호, 관련 드라이버 번호,
날씨 조건, 드라이버 순위/갭 변화를 종합적으로 분석하세요.

[실시간 세션 데이터]
{data}

[사용자 질문]
{question}"""

_NEWS_PROMPT = """당신은 F1 전문가 AI 'F1 Doctor'입니다.
아래 F1 최신 뉴스 검색 결과를 바탕으로 사용자 질문에 **한국어**로 답변하세요.

⚠️ 중요: 검색 결과에 일본어(カタカナ·ひらがな), 중국어(漢字), 아랍어 등 한국어·영어 이외의 문자가 포함되어 있으면 **반드시 한국어로 번역**하여 답변하세요. 원문 외국어 문자를 그대로 출력하지 마세요.

답변 형식:
- 주요 이슈/소식을 **굵은 글씨** 제목으로 구분하여 정리하세요.
- 각 항목은 간결하게 2~3문장으로 요약하세요.
- 검색 결과에 없는 내용은 추측하지 마세요.
- 마지막에 "출처: 웹 검색 (DuckDuckGo)" 를 한 줄 추가하세요.

[F1 최신 뉴스 검색 결과]
{data}

[사용자 질문]
{question}"""

def _build_news_query(msg: str) -> str:
    """메시지 키워드를 분석해 최적의 F1 뉴스 검색 쿼리를 구성합니다."""
    base = f"F1 Formula 1 {CURRENT_SEASON}"
    if any(k in msg for k in ['이적', '계약', '트랜스퍼', 'transfer', '드라이버 변경']):
        return f"{base} driver transfer contract signing news"
    if any(k in msg for k in ['사고', '충돌', '크래시', 'crash', 'accident', '리타이어']):
        return f"{base} crash incident accident retirement"
    if any(k in msg for k in ['페널티', '처벌', '조사', 'penalty', 'investigation', '스튜어드']):
        return f"{base} penalty stewards investigation decision"
    if any(k in msg for k in ['개발', '업그레이드', '파츠', 'upgrade', 'development', '신차']):
        return f"{base} car development upgrade technical news"
    if any(k in msg for k in ['챔피언십', '타이틀', '포인트', 'championship', 'title']):
        return f"{base} championship standings points news"
    if any(k in msg for k in ['프리시즌', '테스트', 'preseason', 'testing', '바르셀로나']):
        return f"{base} pre-season testing Bahrain news"
    if any(k in msg for k in ['팀', '컨스트럭터', 'team']):
        return f"{base} team constructor news update"
    return f"{base} latest news updates recent"


def _try_direct_answer(message: str) -> str | None:
    """
    구조화된 F1 쿼리를 감지하여 F1 API / 뉴스 검색 / 실시간 세션 데이터를 직접 호출하고,
    에이전트(도구 호출) 없이 LLM만으로 답변을 생성합니다.
    매칭되지 않으면 None을 반환하여 에이전트가 처리하도록 합니다.
    """
    msg = message.lower()
    api_data:  str | None = None
    news_data: str | None = None
    live_data: str | None = None

    # ① 시즌 일정 / 캘린더 / 다음 레이스
    if any(k in msg for k in [
        '시즌 일정', '레이스 일정', '캘린더', '다음 레이스', '다음 경기',
        'schedule', 'calendar', '레이스 스케줄', '그랑프리 일정', '2026 일정',
        '시즌 캘린더', '레이스 캘린더'
    ]):
        try:
            raw = get_race_schedule.invoke({"season": CURRENT_SEASON})
            if _api_ok(raw):
                api_data = raw
        except Exception:
            pass

    # ② 드라이버 챔피언십 순위
    elif any(k in msg for k in [
        '드라이버 순위', '드라이버 챔피언십', '드라이버 스탠딩', '포인트 순위', 'driver standing'
    ]):
        try:
            raw = get_driver_standings.invoke({"season": "current"})
            if _api_ok(raw):
                api_data = raw
        except Exception:
            pass

    # ③ 컨스트럭터 / 팀 순위
    elif any(k in msg for k in [
        '컨스트럭터 순위', '팀 순위', '팀 챔피언십', '컨스트럭터 스탠딩', 'constructor standing'
    ]):
        try:
            raw = get_constructor_standings.invoke({"season": "current"})
            if _api_ok(raw):
                api_data = raw
        except Exception:
            pass

    # ④ 최근 레이스 결과
    elif any(k in msg for k in [
        '레이스 결과', '최근 레이스', '최근 경기', '지난 레이스', '지난 경기',
        '우승자', '최근 그랑프리', '레이스 우승'
    ]):
        try:
            raw = get_race_results.invoke({"season": "current", "round_num": "last"})
            if _api_ok(raw):
                api_data = raw
        except Exception:
            pass

    # ⑤ 예선 결과
    elif any(k in msg for k in [
        '예선 결과', '퀄리파잉', '그리드 순서', 'qualifying result', '폴 포지션'
    ]):
        try:
            raw = get_qualifying_results.invoke({"season": "current", "round_num": "last"})
            if _api_ok(raw):
                api_data = raw
        except Exception:
            pass

    # ⑥ 최신 뉴스 / 소식 / 이슈 (웹 검색 — F1 접두어 보장)
    elif any(k in msg for k in [
        '뉴스', '소식', '이슈', '루머', '이적', '화제', '논란', '근황',
        '최신 소식', '어떤 일', '어떤 이슈', '최근 소식', '최근 이슈',
        '이번 시즌 소식', '팀 소식', '드라이버 소식', '요즘', '근래',
        '이번 주', '이번 달', '프리시즌', '테스트 소식'
    ]):
        try:
            query = _build_news_query(msg)
            result = _run_search(query)
            if result and _is_f1_content(result):
                news_data = result
        except Exception:
            pass

    # ⑦ 실시간 세션 질문 (사고·깃발·세이프티카·현재 상황 등)
    elif any(k in msg for k in [
        # 현재 시제 / 즉시성 (명확한 라이브 키워드)
        '방금', '지금', '현재', '실시간', '이번 세션', '이번 랩',
        # 실시간 이벤트
        '세이프티카', '버추얼 세이프티카', 'vsc', 'sc 나왔',
        '적기', '황기', '청기', '깃발',
        '사고', '충돌', '크래시', '리타이어', '리타이어먼트',
        '인시던트', '조사 중', '페널티 받',
        # 현재 상태 질문
        '현재 상황', '지금 상황', '현재 순위', '지금 순위',
        '현재 갭', '지금 몇 등', '현재 날씨',
    ]):
        live_ctx = _fetch_live_context()
        if live_ctx:
            live_data = live_ctx
        else:
            # 라이브 세션 없음 — 명확한 "지금/현재/실시간" 키워드 없으면 뉴스 검색으로 폴백
            live_only_keywords = ['방금', '지금', '현재', '실시간', '이번 세션', '이번 랩',
                                  '현재 상황', '지금 상황', '현재 순위', '지금 순위',
                                  '현재 갭', '지금 몇 등', '현재 날씨', 'sc 나왔']
            if any(k in msg for k in live_only_keywords):
                return (
                    "현재 진행 중인 F1 세션이 없습니다. 📡\n\n"
                    "프랙티스·퀄리파잉·레이스 세션 중에 다시 질문해 주세요.\n"
                    "실시간 데이터는 **[Live Telemetry](/telemetry)** 탭에서도 확인할 수 있습니다."
                )
            # 사고/충돌 등 과거 이벤트 관련 → 뉴스 검색으로 처리
            try:
                query = _build_news_query(msg)
                result = _run_search(query)
                if result and _is_f1_content(result):
                    news_data = result
            except Exception:
                pass

    # ── 결과 반환 ──
    if api_data:
        try:
            prompt = _DIRECT_PROMPT.format(data=api_data, question=message)
            response = llm.invoke(prompt)
            return response.content
        except Exception:
            pass

    if news_data:
        try:
            prompt = _NEWS_PROMPT.format(data=news_data, question=message)
            response = llm.invoke(prompt)
            return _strip_japanese(response.content)
        except Exception:
            pass

    if live_data:
        try:
            prompt = _LIVE_PROMPT.format(data=live_data, question=message)
            response = llm.invoke(prompt)
            return response.content
        except Exception:
            pass

    return None


# ── 웹 검색 폴백 헬퍼 ─────────────────────────────────────────────────
def _web_search_fallback(query: str) -> str:
    try:
        result = _run_search(query)
        summary_prompt = (
            f"당신은 F1 전문가 AI입니다. 다음 F1 웹 검색 결과를 바탕으로 "
            f"'{query}' 질문에 **한국어**로 간결하게 답변해 주세요:\n\n{result}"
        )
        response = llm.invoke(summary_prompt)
        return response.content
    except Exception as e:
        return f"죄송합니다. 정보를 찾지 못했습니다. 직접 검색해 보시기 바랍니다. (오류: {str(e)[:100]})"

# ── 엔드포인트 ────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def home():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    """서버 상태 확인 엔드포인트"""
    return {"status": "ok"}

@app.get("/telemetry", include_in_schema=False)
def telemetry_page():
    return FileResponse("static/telemetry.html")

@app.post("/chat")
def chat(request: ChatRequest):
    """웹 UI용 채팅 엔드포인트 (대화 히스토리 유지)"""
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # 구조화된 F1 쿼리는 에이전트 없이 직접 처리
    direct = _try_direct_answer(request.message)
    if direct:
        return {"question": request.message, "answer": direct, "thread_id": thread_id}

    try:
        response = agent_executor.invoke({"messages": [("human", request.message)]}, config=config)
        answer = response["messages"][-1].content
        return {"question": request.message, "answer": answer, "thread_id": thread_id}
    except Exception as e:
        error_msg = str(e)
        if "tool_use_failed" in error_msg or "Failed to call a function" in error_msg:
            answer = _web_search_fallback(request.message)
            return {"question": request.message, "answer": answer, "thread_id": thread_id}
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """스트리밍 채팅 엔드포인트 (Server-Sent Events)"""
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # 구조화된 F1 쿼리는 에이전트 없이 직접 처리 (SSE로 스트리밍)
    # asyncio.to_thread: _try_direct_answer는 동기(blocking) 함수 — event loop 블록 방지
    import asyncio
    direct = await asyncio.to_thread(_try_direct_answer, request.message)
    if direct:
        async def direct_stream():
            chunk_size = 30
            for i in range(0, len(direct), chunk_size):
                yield f"data: {json.dumps({'token': direct[i:i+chunk_size], 'thread_id': thread_id})}\n\n"
            yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"
        return StreamingResponse(
            direct_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    async def event_stream():
        try:
            async for event in agent_executor.astream_events(
                {"messages": [("human", request.message)]},
                config=config,
                version="v2"
            ):
                if event["event"] == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    content = chunk.content
                    # 도구 호출 청크 제외, 텍스트 응답만 스트리밍
                    has_tool_calls = bool(getattr(chunk, "tool_call_chunks", []))
                    if content and isinstance(content, str) and not has_tool_calls:
                        yield f"data: {json.dumps({'token': content, 'thread_id': thread_id})}\n\n"

            yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"

        except Exception as e:
            error_msg = str(e)
            # tool_use_failed → 웹 검색 폴백
            if "tool_use_failed" in error_msg or "Failed to call a function" in error_msg:
                fallback = _web_search_fallback(request.message)
                yield f"data: {json.dumps({'token': fallback, 'thread_id': thread_id})}\n\n"
                yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"
            else:
                yield f"data: {json.dumps({'error': error_msg[:200]})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
