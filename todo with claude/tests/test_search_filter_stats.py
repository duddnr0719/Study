"""검색, 필터, 정렬, 페이지네이션, 통계 API 테스트."""


def _create_task(client, **overrides):
    payload = {"title": "기본", **overrides}
    resp = client.post("/api/v1/tasks", json=payload)
    assert resp.status_code == 201
    return resp.json()


def _seed_tasks(client):
    """다양한 태스크 5개 생성 (테스트 데이터)."""
    tasks = [
        {"title": "보고서 작성", "status": "todo", "priority": "high", "tags": ["업무", "문서"]},
        {"title": "운동하기", "status": "in_progress", "priority": "medium", "tags": ["건강"]},
        {"title": "장보기", "status": "done", "priority": "low", "tags": ["생활"]},
        {"title": "코드 리뷰", "status": "todo", "priority": "urgent", "tags": ["업무", "개발"]},
        {"title": "보고서 검토", "status": "in_progress", "priority": "high", "tags": ["업무", "문서"], "description": "분기 보고서 최종 검토"},
    ]
    return [_create_task(client, **t) for t in tasks]


# ── 상태 필터 ─────────────────────────────────────────────────────


def test_filter_by_status(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"status": "todo"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(t["status"] == "todo" for t in data)


def test_filter_by_status_done(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"status": "done"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── 우선순위 필터 ────────────────────────────────────────────────


def test_filter_by_priority(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"priority": "high"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(t["priority"] == "high" for t in data)


# ── 검색어 (search) ─────────────────────────────────────────────


def test_search_by_title(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"search": "보고서"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = {t["title"] for t in data}
    assert "보고서 작성" in titles
    assert "보고서 검토" in titles


def test_search_by_description(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"search": "분기"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "보고서 검토"


def test_search_no_match(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"search": "존재하지않는키워드"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── 태그 필터 ────────────────────────────────────────────────────


def test_filter_by_tag(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"tag": "업무"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3  # 보고서 작성, 코드 리뷰, 보고서 검토


def test_filter_by_tag_no_match(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"tag": "여행"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── 정렬 ─────────────────────────────────────────────────────────


def test_sort_by_title_asc(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"sort_by": "title", "sort_order": "asc"})
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert titles == sorted(titles)


def test_sort_by_title_desc(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"sort_by": "title", "sort_order": "desc"})
    assert resp.status_code == 200
    titles = [t["title"] for t in resp.json()]
    assert titles == sorted(titles, reverse=True)


# ── 페이지네이션 ─────────────────────────────────────────────────


def test_pagination_limit(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"limit": 2})
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_pagination_skip(client):
    _seed_tasks(client)
    all_resp = client.get("/api/v1/tasks", params={"limit": 100})
    total = len(all_resp.json())

    resp = client.get("/api/v1/tasks", params={"skip": 3, "limit": 100})
    assert resp.status_code == 200
    assert len(resp.json()) == total - 3


# ── 복합 필터 ────────────────────────────────────────────────────


def test_combined_status_and_priority(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"status": "todo", "priority": "high"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "보고서 작성"


def test_combined_search_and_tag(client):
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks", params={"search": "보고서", "tag": "문서"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


# ── GET /api/v1/tasks/stats ──────────────────────────────────────


def test_stats_empty(client):
    """태스크 없을 때 통계."""
    resp = client.get("/api/v1/tasks/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["by_status"] == {}
    assert data["by_priority"] == {}
    assert data["overdue"] == 0
    assert data["completed_today"] == 0
    assert data["completion_rate"] == 0.0


def test_stats_with_tasks(client):
    """태스크가 있을 때 통계 확인."""
    _seed_tasks(client)
    resp = client.get("/api/v1/tasks/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 5
    # 상태별: todo=2, in_progress=2, done=1
    assert data["by_status"]["todo"] == 2
    assert data["by_status"]["in_progress"] == 2
    assert data["by_status"]["done"] == 1
    # 우선순위별: high=2, medium=1, low=1, urgent=1
    assert data["by_priority"]["high"] == 2
    assert data["by_priority"]["medium"] == 1
    assert data["by_priority"]["low"] == 1
    assert data["by_priority"]["urgent"] == 1
    # 완료율: 1/5 = 20.0%
    assert data["completion_rate"] == 20.0


def test_stats_overdue(client):
    """마감 지난 미완료 태스크 카운트."""
    _create_task(
        client,
        title="지난 태스크",
        status="todo",
        due_date="2020-01-01T00:00:00Z",
    )
    _create_task(
        client,
        title="완료된 과거",
        status="done",
        due_date="2020-01-01T00:00:00Z",
    )
    resp = client.get("/api/v1/tasks/stats")
    data = resp.json()
    assert data["overdue"] == 1  # done은 overdue에 포함 안 됨
