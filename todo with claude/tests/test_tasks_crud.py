"""Task CRUD API 테스트."""

import uuid


def _create_task(client, **overrides):
    """헬퍼: 태스크 생성 후 응답 JSON 반환."""
    payload = {"title": "테스트 태스크", **overrides}
    resp = client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── POST /api/v1/tasks ──────────────────────────────────────────


def test_create_task_minimal(client):
    """필수 필드만으로 태스크 생성."""
    data = _create_task(client)
    assert data["title"] == "테스트 태스크"
    assert data["status"] == "todo"
    assert data["priority"] == "medium"
    assert data["tags"] == []
    assert data["id"] is not None


def test_create_task_full(client):
    """모든 필드를 채워 태스크 생성."""
    data = _create_task(
        client,
        title="풀 태스크",
        description="상세 설명",
        status="in_progress",
        priority="high",
        tags=["work", "urgent"],
        due_date="2026-03-01T09:00:00Z",
        estimated_duration=120,
    )
    assert data["title"] == "풀 태스크"
    assert data["description"] == "상세 설명"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"
    assert data["tags"] == ["work", "urgent"]
    assert data["estimated_duration"] == 120


def test_create_task_validation_empty_title(client):
    """빈 제목 → 422."""
    resp = client.post("/api/v1/tasks", json={"title": ""})
    assert resp.status_code == 422


def test_create_task_validation_no_title(client):
    """제목 누락 → 422."""
    resp = client.post("/api/v1/tasks", json={})
    assert resp.status_code == 422


def test_create_task_invalid_status(client):
    """잘못된 상태값 → 422."""
    resp = client.post("/api/v1/tasks", json={"title": "t", "status": "invalid"})
    assert resp.status_code == 422


def test_create_task_invalid_priority(client):
    """잘못된 우선순위 → 422."""
    resp = client.post("/api/v1/tasks", json={"title": "t", "priority": "super"})
    assert resp.status_code == 422


# ── GET /api/v1/tasks ────────────────────────────────────────────


def test_list_tasks_empty(client):
    """빈 목록 조회."""
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_tasks_returns_created(client):
    """생성한 태스크가 목록에 포함."""
    _create_task(client, title="A")
    _create_task(client, title="B")
    resp = client.get("/api/v1/tasks")
    assert resp.status_code == 200
    titles = {t["title"] for t in resp.json()}
    assert titles == {"A", "B"}


# ── GET /api/v1/tasks/{id} ──────────────────────────────────────


def test_get_task_by_id(client):
    """단일 태스크 조회."""
    created = _create_task(client, title="조회 테스트")
    resp = client.get(f"/api/v1/tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "조회 테스트"


def test_get_task_not_found(client):
    """존재하지 않는 태스크 → 404."""
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/tasks/{fake_id}")
    assert resp.status_code == 404


# ── PATCH /api/v1/tasks/{id} ────────────────────────────────────


def test_update_task_partial(client):
    """부분 수정: title만 변경."""
    created = _create_task(client)
    resp = client.patch(
        f"/api/v1/tasks/{created['id']}", json={"title": "수정됨"}
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "수정됨"
    assert resp.json()["status"] == "todo"  # 변경 안 된 필드 유지


def test_update_task_status(client):
    """상태 변경."""
    created = _create_task(client)
    resp = client.patch(
        f"/api/v1/tasks/{created['id']}", json={"status": "done"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_update_task_not_found(client):
    """존재하지 않는 태스크 수정 → 404."""
    fake_id = str(uuid.uuid4())
    resp = client.patch(f"/api/v1/tasks/{fake_id}", json={"title": "x"})
    assert resp.status_code == 404


# ── DELETE /api/v1/tasks/{id} ───────────────────────────────────


def test_delete_task(client):
    """태스크 삭제 → 204, 이후 조회 → 404."""
    created = _create_task(client)
    resp = client.delete(f"/api/v1/tasks/{created['id']}")
    assert resp.status_code == 204
    # 삭제 확인
    resp = client.get(f"/api/v1/tasks/{created['id']}")
    assert resp.status_code == 404


def test_delete_task_not_found(client):
    """존재하지 않는 태스크 삭제 → 404."""
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/tasks/{fake_id}")
    assert resp.status_code == 404
