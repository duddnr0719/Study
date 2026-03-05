"""AI 파싱/추천, Notion 동기화 엔드포인트 테스트 (외부 서비스 mock)."""

from unittest.mock import MagicMock, patch


def _create_task(client, **overrides):
    payload = {"title": "기본", **overrides}
    resp = client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ═══════════════════════════════════════════════════════════════════
#  AI: POST /api/v1/tasks/parse
# ═══════════════════════════════════════════════════════════════════


@patch("app.api.tasks.parse_natural_language")
def test_parse_creates_task(mock_parse, client):
    """AI 파싱 성공 → 태스크 생성."""
    mock_parse.return_value = {
        "title": "보고서 작성",
        "description": "분기 보고서",
        "priority": "high",
        "tags": ["업무"],
        "due_date": None,
        "estimated_duration": 60,
    }
    resp = client.post("/api/v1/tasks/parse", json={"text": "내일까지 보고서 작성 급함"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "보고서 작성"
    assert data["priority"] == "high"
    assert data["tags"] == ["업무"]
    assert data["estimated_duration"] == 60
    assert "원본 입력" in data["ai_suggestion"]
    mock_parse.assert_called_once_with("내일까지 보고서 작성 급함")


@patch("app.api.tasks.parse_natural_language")
def test_parse_ai_failure(mock_parse, client):
    """AI 서비스 장애 → 502."""
    mock_parse.side_effect = RuntimeError("API key missing")
    resp = client.post("/api/v1/tasks/parse", json={"text": "뭔가 할 일"})
    assert resp.status_code == 502
    assert "AI 파싱 실패" in resp.json()["detail"]


def test_parse_validation_empty_text(client):
    """빈 텍스트 → 422."""
    resp = client.post("/api/v1/tasks/parse", json={"text": ""})
    assert resp.status_code == 422


def test_parse_validation_too_short(client):
    """1글자 텍스트 → 422 (min_length=2)."""
    resp = client.post("/api/v1/tasks/parse", json={"text": "a"})
    assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════
#  AI: GET /api/v1/tasks/ai/suggestions
# ═══════════════════════════════════════════════════════════════════


def test_suggestions_no_tasks(client):
    """미완료 태스크 없음 → 기본 메시지."""
    resp = client.get("/api/v1/tasks/ai/suggestions")
    assert resp.status_code == 200
    assert "미완료 태스크가 없습니다" in resp.json()["suggestion"]


@patch("app.api.tasks.suggest_task_improvements")
def test_suggestions_with_tasks(mock_suggest, client):
    """미완료 태스크 있을 때 AI 추천 반환."""
    _create_task(client, title="할 일 1", status="todo")
    _create_task(client, title="할 일 2", status="in_progress")

    mock_suggest.return_value = "1순위: 할 일 1을 먼저 완료하세요."
    resp = client.get("/api/v1/tasks/ai/suggestions")
    assert resp.status_code == 200
    assert "1순위" in resp.json()["suggestion"]
    mock_suggest.assert_called_once()


@patch("app.api.tasks.suggest_task_improvements")
def test_suggestions_ai_failure(mock_suggest, client):
    """AI 추천 실패 → 502."""
    _create_task(client, title="할 일", status="todo")
    mock_suggest.side_effect = RuntimeError("API error")
    resp = client.get("/api/v1/tasks/ai/suggestions")
    assert resp.status_code == 502
    assert "AI 추천 생성 실패" in resp.json()["detail"]


@patch("app.api.tasks.suggest_task_improvements")
def test_suggestions_excludes_done_tasks(mock_suggest, client):
    """완료된 태스크는 AI 분석 대상에서 제외."""
    _create_task(client, title="완료됨", status="done")
    resp = client.get("/api/v1/tasks/ai/suggestions")
    assert resp.status_code == 200
    # done만 있으므로 AI 호출 없이 기본 메시지 반환
    assert "미완료 태스크가 없습니다" in resp.json()["suggestion"]
    mock_suggest.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
#  Notion: POST /api/v1/tasks/{id}/sync
# ═══════════════════════════════════════════════════════════════════


@patch("app.api.tasks.sync_task_to_notion")
def test_sync_single_task_success(mock_sync, client):
    """Notion 단일 동기화 성공."""
    task = _create_task(client, title="노션 동기화 테스트")
    mock_sync.return_value = "fake-notion-page-id-123"

    resp = client.post(f"/api/v1/tasks/{task['id']}/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["notion_page_id"] == "fake-notion-page-id-123"
    mock_sync.assert_called_once()


@patch("app.api.tasks.sync_task_to_notion")
def test_sync_single_task_failure(mock_sync, client):
    """Notion 동기화 실패 → 502."""
    task = _create_task(client, title="실패 테스트")
    mock_sync.return_value = None

    resp = client.post(f"/api/v1/tasks/{task['id']}/sync")
    assert resp.status_code == 502
    assert "Notion 동기화 실패" in resp.json()["detail"]


# ═══════════════════════════════════════════════════════════════════
#  Notion: POST /api/v1/tasks/sync/all
# ═══════════════════════════════════════════════════════════════════


@patch("app.api.tasks.sync_task_to_notion")
def test_sync_all_tasks(mock_sync, client):
    """미완료 태스크 전체 동기화."""
    _create_task(client, title="할 일 1", status="todo")
    _create_task(client, title="진행 중", status="in_progress")
    _create_task(client, title="완료됨", status="done")  # 제외 대상

    mock_sync.return_value = "notion-page-id"
    resp = client.post("/api/v1/tasks/sync/all")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2  # done 제외
    assert all(t["notion_page_id"] == "notion-page-id" for t in data)


@patch("app.api.tasks.sync_task_to_notion")
def test_sync_all_partial_failure(mock_sync, client):
    """일부만 동기화 성공."""
    _create_task(client, title="성공", status="todo")
    _create_task(client, title="실패", status="todo")

    # 첫 번째 호출 성공, 두 번째 실패
    mock_sync.side_effect = ["notion-id-1", None]
    resp = client.post("/api/v1/tasks/sync/all")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1  # 성공한 것만


# ═══════════════════════════════════════════════════════════════════
#  Notion: POST /api/v1/tasks/sync/from-notion
# ═══════════════════════════════════════════════════════════════════


@patch("app.api.tasks.fetch_tasks_from_notion")
def test_import_from_notion(mock_fetch, client):
    """Notion에서 태스크 가져오기."""
    mock_fetch.return_value = [
        {
            "notion_page_id": "page-1",
            "title": "노션 태스크 1",
            "status": "todo",
            "priority": "high",
            "tags": ["노션"],
            "due_date": None,
            "ai_suggestion": None,
        },
        {
            "notion_page_id": "page-2",
            "title": "노션 태스크 2",
            "status": "in_progress",
            "priority": "medium",
            "tags": [],
            "due_date": None,
            "ai_suggestion": None,
        },
    ]
    resp = client.post("/api/v1/tasks/sync/from-notion")
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 2
    assert data[0]["title"] == "노션 태스크 1"
    assert data[0]["notion_page_id"] == "page-1"
    assert data[1]["title"] == "노션 태스크 2"


@patch("app.api.tasks.fetch_tasks_from_notion")
def test_import_from_notion_updates_existing(mock_fetch, client):
    """이미 동기화된 태스크는 업데이트."""
    # 먼저 Notion page ID가 있는 태스크 직접 가져오기
    mock_fetch.return_value = [
        {
            "notion_page_id": "existing-page",
            "title": "원래 제목",
            "status": "todo",
            "priority": "medium",
            "tags": [],
            "due_date": None,
            "ai_suggestion": None,
        },
    ]
    resp = client.post("/api/v1/tasks/sync/from-notion")
    assert resp.status_code == 201
    assert len(resp.json()) == 1

    # 두 번째 import: 같은 notion_page_id → 업데이트
    mock_fetch.return_value = [
        {
            "notion_page_id": "existing-page",
            "title": "변경된 제목",
            "status": "in_progress",
            "priority": "high",
            "tags": ["업데이트"],
            "due_date": None,
            "ai_suggestion": None,
        },
    ]
    resp = client.post("/api/v1/tasks/sync/from-notion")
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "변경된 제목"
    assert data[0]["status"] == "in_progress"

    # 전체 목록에서도 1개만 있어야 함 (중복 생성 아님)
    all_tasks = client.get("/api/v1/tasks").json()
    notion_tasks = [t for t in all_tasks if t["notion_page_id"] == "existing-page"]
    assert len(notion_tasks) == 1


@patch("app.api.tasks.fetch_tasks_from_notion")
def test_import_from_notion_empty(mock_fetch, client):
    """Notion에 태스크 없을 때."""
    mock_fetch.return_value = []
    resp = client.post("/api/v1/tasks/sync/from-notion")
    assert resp.status_code == 201
    assert resp.json() == []
