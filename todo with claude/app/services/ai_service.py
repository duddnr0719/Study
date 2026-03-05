import json
from datetime import UTC, datetime

import anthropic

from app.core.config import get_settings


def _get_client() -> anthropic.Anthropic:
    settings = get_settings()
    return anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def parse_natural_language(text: str) -> dict:
    """자연어 입력을 구조화된 태스크 데이터로 변환.

    예: "내일까지 보고서 작성 급함" → {title, due_date, priority, tags, ...}
    """
    settings = get_settings()
    client = _get_client()
    now = datetime.now(UTC).isoformat()

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""다음 자연어 입력에서 태스크 정보를 추출해 JSON으로 반환해줘.
현재 시각: {now}

입력: "{text}"

반드시 아래 JSON 형식만 반환해. 설명이나 마크다운 없이 순수 JSON만.
{{
  "title": "핵심 작업 제목 (간결하게)",
  "description": "부가 설명이 있으면 작성, 없으면 null",
  "priority": "low | medium | high | urgent 중 하나",
  "tags": ["관련 태그들"],
  "due_date": "ISO 8601 형식 또는 null",
  "estimated_duration": "예상 소요 시간(분) 또는 null"
}}""",
            }
        ],
    )

    raw = message.content[0].text.strip()
    # JSON 블록으로 감싸진 경우 추출
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(raw)


def suggest_task_improvements(tasks: list[dict]) -> str:
    """현재 태스크 목록을 분석하고 우선순위 최적화 및 일정 추천을 반환."""
    settings = get_settings()
    client = _get_client()
    now = datetime.now(UTC).isoformat()

    tasks_text = json.dumps(tasks, ensure_ascii=False, indent=2, default=str)

    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": f"""당신은 생산성 전문가입니다. 아래 태스크 목록을 분석해주세요.
현재 시각: {now}

태스크 목록:
{tasks_text}

다음 항목을 간결하게 한국어로 분석해주세요:
1. 우선순위 조정이 필요한 태스크 (있다면)
2. 마감일이 임박하거나 지난 태스크 경고
3. 오늘 집중해야 할 추천 작업 순서
4. 전체적인 워크로드 밸런스 조언

간결하고 실행 가능한 조언 위주로 작성해주세요.""",
            }
        ],
    )

    return message.content[0].text
