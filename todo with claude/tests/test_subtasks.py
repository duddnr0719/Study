"""SubTask API 테스트."""

import uuid


def _create_task(client, **overrides):
    payload = {"title": "부모 태스크", **overrides}
    resp = client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    return resp.json()


def _create_subtask(client, task_id, **overrides):
    payload = {"title": "서브태스크", **overrides}
    resp = client.post(f"/api/v1/tasks/{task_id}/subtasks", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── POST /api/v1/tasks/{task_id}/subtasks ────────────────────────


def test_create_subtask(client):
    """서브태스크 생성."""
    task = _create_task(client)
    sub = _create_subtask(client, task["id"], title="하위 작업 1", position=0)
    assert sub["title"] == "하위 작업 1"
    assert sub["is_completed"] is False
    assert sub["position"] == 0
    assert sub["task_id"] == task["id"]


def test_create_subtask_parent_not_found(client):
    """부모 태스크 없음 → 404."""
    fake_id = str(uuid.uuid4())
    resp = client.post(
        f"/api/v1/tasks/{fake_id}/subtasks",
        json={"title": "orphan"},
    )
    assert resp.status_code == 404


def test_create_subtask_validation_empty_title(client):
    """빈 제목 → 422."""
    task = _create_task(client)
    resp = client.post(
        f"/api/v1/tasks/{task['id']}/subtasks",
        json={"title": ""},
    )
    assert resp.status_code == 422


# ── GET /api/v1/tasks/{task_id}/subtasks ─────────────────────────


def test_list_subtasks_empty(client):
    """서브태스크 없을 때 빈 목록."""
    task = _create_task(client)
    resp = client.get(f"/api/v1/tasks/{task['id']}/subtasks")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_subtasks_ordered(client):
    """position 순서대로 반환."""
    task = _create_task(client)
    _create_subtask(client, task["id"], title="B", position=2)
    _create_subtask(client, task["id"], title="A", position=1)
    _create_subtask(client, task["id"], title="C", position=3)

    resp = client.get(f"/api/v1/tasks/{task['id']}/subtasks")
    assert resp.status_code == 200
    titles = [s["title"] for s in resp.json()]
    assert titles == ["A", "B", "C"]


# ── PATCH /api/v1/tasks/{task_id}/subtasks/{subtask_id} ──────────


def test_update_subtask_complete(client):
    """서브태스크 완료 처리."""
    task = _create_task(client)
    sub = _create_subtask(client, task["id"])
    resp = client.patch(
        f"/api/v1/tasks/{task['id']}/subtasks/{sub['id']}",
        json={"is_completed": True},
    )
    assert resp.status_code == 200
    assert resp.json()["is_completed"] is True


def test_update_subtask_title(client):
    """서브태스크 제목 변경."""
    task = _create_task(client)
    sub = _create_subtask(client, task["id"], title="원래 제목")
    resp = client.patch(
        f"/api/v1/tasks/{task['id']}/subtasks/{sub['id']}",
        json={"title": "변경된 제목"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "변경된 제목"


def test_update_subtask_not_found(client):
    """존재하지 않는 서브태스크 수정 → 404."""
    task = _create_task(client)
    fake_id = str(uuid.uuid4())
    resp = client.patch(
        f"/api/v1/tasks/{task['id']}/subtasks/{fake_id}",
        json={"title": "x"},
    )
    assert resp.status_code == 404


# ── DELETE /api/v1/tasks/{task_id}/subtasks/{subtask_id} ─────────


def test_delete_subtask(client):
    """서브태스크 삭제."""
    task = _create_task(client)
    sub = _create_subtask(client, task["id"])
    resp = client.delete(f"/api/v1/tasks/{task['id']}/subtasks/{sub['id']}")
    assert resp.status_code == 204

    # 삭제 확인
    resp = client.get(f"/api/v1/tasks/{task['id']}/subtasks")
    assert resp.json() == []


def test_delete_subtask_not_found(client):
    """존재하지 않는 서브태스크 삭제 → 404."""
    task = _create_task(client)
    fake_id = str(uuid.uuid4())
    resp = client.delete(f"/api/v1/tasks/{task['id']}/subtasks/{fake_id}")
    assert resp.status_code == 404


# ── Cascade delete ───────────────────────────────────────────────


def test_cascade_delete_parent_removes_subtasks(client):
    """부모 태스크 삭제 시 서브태스크도 함께 삭제."""
    task = _create_task(client)
    _create_subtask(client, task["id"], title="sub1")
    _create_subtask(client, task["id"], title="sub2")

    # 부모 삭제
    resp = client.delete(f"/api/v1/tasks/{task['id']}")
    assert resp.status_code == 204

    # 부모가 없으니 서브태스크 조회도 404
    resp = client.get(f"/api/v1/tasks/{task['id']}/subtasks")
    assert resp.status_code == 404


# ── 태스크 조회 시 서브태스크 포함 ────────────────────────────────


def test_task_response_includes_subtasks(client):
    """태스크 단일 조회 시 subtasks 필드에 서브태스크 포함."""
    task = _create_task(client)
    _create_subtask(client, task["id"], title="s1", position=1)
    _create_subtask(client, task["id"], title="s2", position=2)

    resp = client.get(f"/api/v1/tasks/{task['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["subtasks"]) == 2
    assert data["subtasks"][0]["title"] == "s1"
    assert data["subtasks"][1]["title"] == "s2"
