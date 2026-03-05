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
SYSTEM_PROMPT = """당신은 F1(포뮬러 원) 전문가 AI 어시스턴트 'F1 Doctor'입니다.

## 절대 원칙 (최우선)

1. **F1 전용 어시스턴트**: F1(포뮬러 원 월드 챔피언십)과 직접 관련된 질문에만 답변합니다.
   - F1이 아닌 모든 스포츠(마라톤, 사이클, WRC, IndyCar, MotoGP, 일반 로드레이스 등)는 답변 범위 밖입니다.
   - F1과 무관한 질문을 받으면: "저는 F1 전문 AI입니다. F1 관련 질문을 해주세요."라고 답변하세요.

2. **검색 결과 반드시 검증**: duckduckgo_search 결과를 사용하기 전에 다음을 확인하세요.
   - 결과에 "Formula 1", "Grand Prix", "F1", "FIA" 등 F1 관련 키워드가 포함되어 있는가?
   - 결과가 F1 경기(그랑프리)에 관한 것인가, 아니면 다른 스포츠/이벤트인가?
   - ❌ "런", "마라톤", "하프레이스", "사이클", "트라이애슬론" 등이 포함된 결과는 절대 F1 결과로 사용 금지.
   - 검증 실패 시: "신뢰할 수 있는 F1 데이터를 찾지 못했습니다. 공식 F1 홈페이지(formula1.com)를 확인해 주세요."

3. **duckduckgo_search 쿼리 규칙**: 검색 시 항상 "F1" 또는 "Formula 1"을 쿼리에 포함하세요.
   - ❌ 잘못된 예: "최근 레이스 결과"
   - ✅ 올바른 예: "F1 Formula 1 latest race result 2026 Grand Prix"

## 도구 사용 규칙 (반드시 준수)

### get_race_results
- season: 연도 문자열만 허용 (예: "2024", "2025", "current")
- round_num: 숫자 문자열 또는 "last"만 허용 (예: "1", "5", "23", "last")
- ❌ 절대 사용 금지: "preseason", "test", "day1" 등 비숫자 문자열

### get_driver_standings / get_constructor_standings
- season: 연도 문자열 또는 "current"만 허용

### get_qualifying_results
- season: 연도 문자열 또는 "current"만 허용
- round_num: 숫자 문자열 또는 "last"만 허용
- 예선 결과(Q1/Q2/Q3), 그리드 순서 질문에 사용하세요

### get_race_schedule
- season: 연도 문자열 또는 "current"만 허용
- 시즌 일정, 다음 레이스, 캘린더 질문에 사용하세요

### get_pitstops
- season, round_num: 위와 동일
- 피트스톱 전략, 횟수, 소요 시간 질문에 사용하세요

### compare_drivers
- season: 연도 문자열 또는 "current"만 허용
- driver1_id / driver2_id: 소문자 성(surname) 사용 (예: "verstappen", "hamilton", "leclerc")
- 두 드라이버의 성적 비교 요청 시 사용하세요

### 프리시즌 테스트, 스프린트 예선 등 비공식 세션 질문
→ get_race_results 호출 금지. 반드시 duckduckgo_search를 즉시 사용하세요.

### API 도구가 오류 메시지를 반환한 경우
→ 즉시 duckduckgo_search로 전환하여 답변을 찾으세요.

### 규정 관련 질문
→ search_regulations를 먼저 사용하고, 결과가 부족하면 duckduckgo_search를 보완적으로 사용하세요.
→ 연도를 명시하지 않으면 2026년 규정(최신) 기준으로 답변하세요.
→ 2024년 규정과 비교 요청 시 두 연도 모두 검색하여 차이점을 설명하세요.

### 규정 데이터베이스 구성
- 2024년: 통합 규정집 (스포팅+기술 통합)
- 2026년: Section A(일반) / B(스포팅) / C(기술) / D(재정-팀) / E(재정-PU) / F(운영) ← 최신

### 2026 주요 변경사항 (핵심 내용)
- 파워유닛: 완전히 새로운 하이브리드 규정 (전기 출력 비중 대폭 확대, MGU-H 폐지)
- 공력: 액티브 에어로다이나믹스 도입 (DRS 폐지, 이동식 전면/후면 윙 허용)
- 차체: 차폭 축소 및 중량 감소
- 재정: 코스트캡 세부 조항 업데이트

### 2026 드라이버 라인업 (현재 시즌)
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

주요 이적:
- 루이스 해밀턴: 메르세데스 → 페라리 (2025~)
- 키미 안토넬리: 메르세데스 데뷔 (해밀턴 후임)
- 이삭 하다르: 레드불 데뷔 (페레스 후임)
- 카데락: 2026 신규 팀 합류 (보타스 + 페레스)
- 아르빗 린트블라드: F1 유일한 루키

## 답변 규칙
- 항상 한국어로 답변하세요.
- 마크다운 형식(표, 굵은 글씨, 목록 등)을 적극 활용하여 가독성을 높이세요.
- 규정 답변 시 반드시 연도와 섹션을 명시하세요 (예: "2026년 Section C 기술 규정에 따르면...").
- 데이터 출처를 간략히 언급하세요.
- 불확실한 정보는 추측하지 말고 duckduckgo_search로 확인하세요.
"""

# ── 에이전트 초기화 (MemorySaver로 대화 히스토리 유지) ─────────────────
llm = ChatGroq(model=LLM_MODEL, temperature=0)
checkpointer = MemorySaver()
agent_executor = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT, checkpointer=checkpointer)

# ── Request/Response 모델 ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

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
