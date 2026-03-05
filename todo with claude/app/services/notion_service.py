from datetime import UTC, datetime

import httpx

from app.core.config import get_settings

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# 백엔드 → Notion 매핑
STATUS_MAP = {
    "todo": "시작 안 함",
    "in_progress": "진행 중",
    "done": "완료",
}
STATUS_REVERSE = {v: k for k, v in STATUS_MAP.items()}

PRIORITY_MAP = {
    "low": "낮음",
    "medium": "보통",
    "high": "높음",
    "urgent": "높음",  # Notion에 "긴급"이 없으므로 "높음"으로 매핑
}
PRIORITY_REVERSE = {"낮음": "low", "보통": "medium", "높음": "high"}


def _headers() -> dict:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.notion_api_key.get_secret_value()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _build_page_properties(task) -> dict:
    """Task 객체를 Notion 페이지 속성으로 변환."""
    props: dict = {
        "할 일": {"title": [{"text": {"content": task.title}}]},
        "상태": {"status": {"name": STATUS_MAP.get(task.status, "시작 안 함")}},
        "우선순위": {
            "select": {"name": PRIORITY_MAP.get(task.priority, "보통")}
        },
    }

    if task.tags:
        props["카테고리"] = {
            "multi_select": [{"name": tag} for tag in task.tags]
        }

    if task.due_date:
        props["마감일"] = {
            "date": {"start": task.due_date.isoformat()}
        }

    if task.ai_suggestion:
        props["AI 요약"] = {
            "rich_text": [{"text": {"content": task.ai_suggestion[:2000]}}]
        }

    props["마지막 동기화"] = {
        "date": {"start": datetime.now(UTC).isoformat()}
    }

    return props


def sync_task_to_notion(task) -> str | None:
    """태스크를 Notion에 동기화. 새 페이지 생성 또는 기존 페이지 업데이트.

    Returns: Notion page ID 또는 실패 시 None
    """
    settings = get_settings()
    headers = _headers()
    props = _build_page_properties(task)

    if task.notion_page_id:
        # 기존 페이지 업데이트
        r = httpx.patch(
            f"{NOTION_API_URL}/pages/{task.notion_page_id}",
            headers=headers,
            json={"properties": props},
        )
        if r.status_code == 200:
            return task.notion_page_id
        return None

    # 새 페이지 생성
    page_data = {
        "parent": {"database_id": settings.notion_database_id},
        "properties": props,
    }
    r = httpx.post(f"{NOTION_API_URL}/pages", headers=headers, json=page_data)
    if r.status_code == 200:
        return r.json()["id"]
    return None


def fetch_tasks_from_notion() -> list[dict]:
    """Notion DB에서 모든 태스크를 가져와 백엔드 형식으로 변환."""
    settings = get_settings()
    headers = _headers()

    r = httpx.post(
        f"{NOTION_API_URL}/databases/{settings.notion_database_id}/query",
        headers=headers,
        json={},
    )
    if r.status_code != 200:
        return []

    tasks = []
    for page in r.json().get("results", []):
        props = page.get("properties", {})

        # title
        title_parts = props.get("할 일", {}).get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts)
        if not title:
            continue

        # status
        status_name = props.get("상태", {}).get("status", {}).get("name", "시작 안 함")
        status = STATUS_REVERSE.get(status_name, "todo")

        # priority
        priority_obj = props.get("우선순위", {}).get("select")
        priority = PRIORITY_REVERSE.get(
            priority_obj.get("name", "") if priority_obj else "", "medium"
        )

        # tags
        tags = [
            opt.get("name", "")
            for opt in props.get("카테고리", {}).get("multi_select", [])
        ]

        # due_date
        date_obj = props.get("마감일", {}).get("date")
        due_date = date_obj.get("start") if date_obj else None

        # ai_suggestion
        ai_parts = props.get("AI 요약", {}).get("rich_text", [])
        ai_suggestion = "".join(t.get("plain_text", "") for t in ai_parts) or None

        tasks.append({
            "notion_page_id": page["id"],
            "title": title,
            "status": status,
            "priority": priority,
            "tags": tags,
            "due_date": due_date,
            "ai_suggestion": ai_suggestion,
        })

    return tasks


def delete_notion_page(page_id: str) -> bool:
    """Notion 페이지를 휴지통으로 이동 (아카이브)."""
    headers = _headers()
    r = httpx.patch(
        f"{NOTION_API_URL}/pages/{page_id}",
        headers=headers,
        json={"archived": True},
    )
    return r.status_code == 200
