import os
import uuid
import json
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from telemetry import router as telemetry_router

from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool

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
LLM_MODEL       = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
EMBEDDING_MODEL = os.getenv("GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001")
CHROMA_DIR      = os.getenv("CHROMA_DIR", "./chroma_db")

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
search = DuckDuckGoSearchRun()

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
llm = ChatGroq(model=LLM_MODEL, temperature=0)
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

def _api_ok(data: str) -> bool:
    """API 반환값이 실제 데이터인지(오류 메시지가 아닌지) 확인합니다."""
    if not data:
        return False
    error_indicators = ['없음', '실패', 'error', '웹 검색을 사용하세요']
    return not any(ind in data for ind in error_indicators)


# ── 직접 답변 생성 (에이전트 우회) ─────────────────────────────────────
_DIRECT_PROMPT = """당신은 F1 전문가 AI 'F1 Doctor'입니다.
아래 F1 공식 데이터를 바탕으로 사용자 질문에 **한국어**로 답변하세요.
마크다운 표, 굵은 글씨, 목록을 적극 활용하세요.
데이터에 없는 내용은 추측하지 마세요.

[F1 공식 데이터]
{data}

[사용자 질문]
{question}"""

_NEWS_PROMPT = """당신은 F1 전문가 AI 'F1 Doctor'입니다.
아래 F1 최신 뉴스 검색 결과를 바탕으로 사용자 질문에 **한국어**로 답변하세요.

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
    base = "F1 Formula 1 2026"
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
    구조화된 F1 쿼리를 감지하여 F1 API 또는 F1 뉴스 검색을 직접 호출하고,
    에이전트(도구 호출) 없이 LLM만으로 답변을 생성합니다.
    매칭되지 않으면 None을 반환하여 에이전트가 처리하도록 합니다.
    """
    msg = message.lower()
    api_data: str | None = None
    news_data: str | None = None

    # ① 시즌 일정 / 캘린더 / 다음 레이스
    if any(k in msg for k in [
        '시즌 일정', '레이스 일정', '캘린더', '다음 레이스', '다음 경기',
        'schedule', 'calendar', '레이스 스케줄', '그랑프리 일정', '2026 일정',
        '시즌 캘린더', '레이스 캘린더'
    ]):
        try:
            raw = get_race_schedule.invoke({"season": "2026"})
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
            result = search.run(query)
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
            return response.content
        except Exception:
            pass

    return None


# ── 웹 검색 폴백 헬퍼 ─────────────────────────────────────────────────
def _web_search_fallback(query: str) -> str:
    try:
        result = search.run(query)
        summary_prompt = f"다음 웹 검색 결과를 바탕으로 '{query}' 질문에 한국어로 간결하게 답변해 주세요:\n\n{result}"
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
    direct = _try_direct_answer(request.message)
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
