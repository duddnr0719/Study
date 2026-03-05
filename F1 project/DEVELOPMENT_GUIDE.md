# F1 Doctor 프로젝트 고도화 완료 보고 🏎️🤖

본 프로젝트는 기존의 단순 RAG 시스템에서 스스로 도구를 선택해 실행하는 **Agentic AI** 구조로 리팩토링되었습니다.

## 1. 주요 업데이트 사항

### ✅ 에이전트 도구화 (Tools) 완료
기존의 정적 함수들을 LangChain의 `@tool`로 변환하여 LLM이 상황에 맞게 호출할 수 있도록 구현했습니다.
- **`get_driver_standings`**: 드라이버 순위 실시간 조회
- **`get_constructor_standings`**: 팀 순위 실시간 조회
- **`get_race_results`**: 경기 결과 조회
- **`get_live_telemetry`**: 실시간 세션 정보 조회 (OpenF1 API 기초 연동)
- **`search_regulations`**: 로컬 벡터 DB 기반 FIA 규정 검색
- **`duckduckgo_search`**: 최신 뉴스 및 루머 검색 (DuckDuckGo 통합)

### ✅ ReAct 에이전트 구조 도입
`main.py`를 리팩토링하여 **Reasoning + Acting** 루프를 구현했습니다. 이제 AI는 사용자의 질문을 분석한 후, API를 부를지, 규정집을 찾을지, 아니면 인터넷 검색을 할지 스스로 결정합니다.

### ✅ 실시간 뉴스 대응 (Search Tool)
API 키가 필요 없는 `DuckDuckGoSearchRun`을 통합하여 "뉴이가 어디로 이적한대?" 같은 최신 뉴스 질문에도 대응할 수 있습니다.

## 2. 사용 방법
1. 가상환경 활성화: `source venv/bin/activate`
2. 서버 실행: `python3 main.py`
3. 질문 테스트: `http://localhost:8000/ask?query=최신 F1 이적 시장 소식 알려줘`

---
**자비스의 피드백:**
이제 F1 닥터는 단순한 지식 저장소를 넘어, 능동적으로 정보를 찾는 에이전트가 되었습니다. 앞으로 더 정밀한 실시간 데이터를 원하신다면 `f1_api.py`의 `get_live_telemetry` 함수를 확장하여 구체적인 차량 센서 데이터를 가져오도록 고도화할 수 있습니다. 🧐
