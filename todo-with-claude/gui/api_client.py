"""백엔드 API 통신 클라이언트."""

from __future__ import annotations

import requests


class TaskAPIClient:
    """FastAPI 백엔드와 통신하는 HTTP 클라이언트."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self._api = f"{base_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ── 헬스 ──────────────────────────────────────────────────────

    def health(self) -> bool:
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    # ── 태스크 CRUD ───────────────────────────────────────────────

    def create_task(self, data: dict) -> dict:
        r = self.session.post(f"{self._api}/tasks", json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def list_tasks(self, **params) -> list[dict]:
        # None 값 제거
        params = {k: v for k, v in params.items() if v is not None}
        r = self.session.get(f"{self._api}/tasks", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_task(self, task_id: str) -> dict:
        r = self.session.get(f"{self._api}/tasks/{task_id}", timeout=10)
        r.raise_for_status()
        return r.json()

    def update_task(self, task_id: str, data: dict) -> dict:
        r = self.session.patch(f"{self._api}/tasks/{task_id}", json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def delete_task(self, task_id: str) -> None:
        r = self.session.delete(f"{self._api}/tasks/{task_id}", timeout=10)
        r.raise_for_status()

    # ── 통계 ──────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        r = self.session.get(f"{self._api}/tasks/stats", timeout=10)
        r.raise_for_status()
        return r.json()

    # ── 서브태스크 ────────────────────────────────────────────────

    def create_subtask(self, task_id: str, data: dict) -> dict:
        r = self.session.post(f"{self._api}/tasks/{task_id}/subtasks", json=data, timeout=10)
        r.raise_for_status()
        return r.json()

    def list_subtasks(self, task_id: str) -> list[dict]:
        r = self.session.get(f"{self._api}/tasks/{task_id}/subtasks", timeout=10)
        r.raise_for_status()
        return r.json()

    def update_subtask(self, task_id: str, subtask_id: str, data: dict) -> dict:
        r = self.session.patch(
            f"{self._api}/tasks/{task_id}/subtasks/{subtask_id}", json=data, timeout=10
        )
        r.raise_for_status()
        return r.json()

    def delete_subtask(self, task_id: str, subtask_id: str) -> None:
        r = self.session.delete(
            f"{self._api}/tasks/{task_id}/subtasks/{subtask_id}", timeout=10
        )
        r.raise_for_status()

    # ── AI ────────────────────────────────────────────────────────

    def parse_natural_language(self, text: str) -> dict:
        r = self.session.post(f"{self._api}/tasks/parse", json={"text": text}, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_ai_suggestions(self) -> dict:
        r = self.session.get(f"{self._api}/tasks/ai/suggestions", timeout=30)
        r.raise_for_status()
        return r.json()

    # ── Notion ────────────────────────────────────────────────────

    def sync_task(self, task_id: str) -> dict:
        r = self.session.post(f"{self._api}/tasks/{task_id}/sync", timeout=15)
        r.raise_for_status()
        return r.json()

    def sync_all(self) -> list[dict]:
        r = self.session.post(f"{self._api}/tasks/sync/all", timeout=30)
        r.raise_for_status()
        return r.json()

    def import_from_notion(self) -> list[dict]:
        r = self.session.post(f"{self._api}/tasks/sync/from-notion", timeout=30)
        r.raise_for_status()
        return r.json()
