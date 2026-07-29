"""스마트 태스크 매니저 — 메인 데스크톱 앱."""

from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

from gui.api_client import TaskAPIClient
from gui.constants import C, FONT_BODY, FONT_SIDEBAR, FONT_SMALL
from gui.frames.ai_panel import AIPanelFrame
from gui.frames.dashboard import DashboardFrame
from gui.frames.notion_sync import NotionSyncFrame
from gui.frames.task_detail import TaskDetailFrame
from gui.frames.task_form import TaskFormFrame
from gui.frames.task_list import TaskListFrame


class TaskManagerApp:
    """Tkinter 메인 애플리케이션."""

    def __init__(self):
        self.server_process: subprocess.Popen | None = None
        self.api = TaskAPIClient()

        # ── Tk 루트 ──────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.title("스마트 태스크 매니저")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=C["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        atexit.register(self._stop_server)

        # ── 서버 시작 ────────────────────────────────────────────
        self._start_server()

        # ── UI 구성 ──────────────────────────────────────────────
        self._build_sidebar()
        self._build_main()
        self._build_statusbar()
        self._init_frames()
        self.show_frame("dashboard")

    # ═══════════════════════════════════════════════════════════════
    #  서버 관리
    # ═══════════════════════════════════════════════════════════════

    def _is_server_running(self) -> bool:
        return self.api.health()

    def _start_server(self):
        if self._is_server_running():
            return  # 이미 실행 중

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        python = sys.executable

        self.server_process = subprocess.Popen(
            [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 서버 준비 대기
        for _ in range(20):
            if self._is_server_running():
                return
            time.sleep(0.5)

        messagebox.showerror("서버 오류", "백엔드 서버 시작에 실패했습니다.\n수동으로 서버를 실행해주세요.")

    def _stop_server(self):
        if self.server_process and self.server_process.poll() is None:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()

    def _on_close(self):
        self._stop_server()
        self.root.destroy()

    # ═══════════════════════════════════════════════════════════════
    #  UI 구성
    # ═══════════════════════════════════════════════════════════════

    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=C["sidebar"], width=180)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # 앱 타이틀
        tk.Label(
            self.sidebar, text="Task\nManager", font=("Helvetica", 16, "bold"),
            bg=C["sidebar"], fg="white", pady=16,
        ).pack(fill=tk.X)

        tk.Frame(self.sidebar, bg=C["sidebar_hover"], height=1).pack(fill=tk.X, padx=12, pady=4)

        # 네비게이션 버튼
        self.nav_buttons: dict[str, tk.Button] = {}
        nav_items = [
            ("dashboard", "대시보드"),
            ("task_list", "태스크 목록"),
            ("task_form_new", "새 태스크"),
            ("ai_panel", "AI 도구"),
            ("notion_sync", "Notion 동기화"),
        ]
        for name, label in nav_items:
            btn = tk.Button(
                self.sidebar, text=f"  {label}", font=FONT_SIDEBAR,
                bg=C["sidebar"], fg=C["sidebar_text"],
                activebackground=C["sidebar_hover"], activeforeground="white",
                relief=tk.FLAT, anchor="w", padx=16, pady=8,
                command=lambda n=name: self._nav_click(n),
            )
            btn.pack(fill=tk.X, padx=4, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=C["sidebar_hover"]))
            btn.bind("<Leave>", lambda e, b=btn, n=name: b.config(bg=C["sidebar_active"] if n == self._current_nav else C["sidebar"]))
            self.nav_buttons[name] = btn

        self._current_nav = ""

    def _build_main(self):
        self.main_area = tk.Frame(self.root, bg=C["bg"])
        self.main_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _build_statusbar(self):
        self.statusbar = tk.Frame(self.root, bg=C["border"], height=28)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = tk.Label(
            self.statusbar, text="준비됨", font=FONT_SMALL,
            bg=C["border"], fg=C["text_secondary"], anchor="w", padx=12,
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        server_status = "연결됨" if self._is_server_running() else "연결 안 됨"
        self.server_label = tk.Label(
            self.statusbar, text=f"서버: {server_status}", font=FONT_SMALL,
            bg=C["border"], fg=C["success"] if self._is_server_running() else C["danger"], padx=12,
        )
        self.server_label.pack(side=tk.RIGHT)

    def set_status(self, msg: str):
        self.status_label.config(text=msg)

    # ═══════════════════════════════════════════════════════════════
    #  프레임 관리
    # ═══════════════════════════════════════════════════════════════

    def _init_frames(self):
        self.frames: dict[str, tk.Frame] = {}

        self.frames["dashboard"] = DashboardFrame(
            self.main_area, self.api, self.set_status,
        )
        self.frames["task_list"] = TaskListFrame(
            self.main_area, self.api, self.set_status,
            show_detail=lambda tid: self._show_detail(tid),
            show_form=lambda tid=None: self._show_form(tid),
        )
        self.frames["task_form"] = TaskFormFrame(
            self.main_area, self.api, self.set_status,
            go_back=lambda: self.show_frame("task_list"),
        )
        self.frames["task_detail"] = TaskDetailFrame(
            self.main_area, self.api, self.set_status,
            go_back=lambda: self.show_frame("task_list"),
            show_form=lambda tid: self._show_form(tid),
        )
        self.frames["ai_panel"] = AIPanelFrame(
            self.main_area, self.api, self.set_status,
        )
        self.frames["notion_sync"] = NotionSyncFrame(
            self.main_area, self.api, self.set_status,
        )

    def show_frame(self, name: str):
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill=tk.BOTH, expand=True)
        if hasattr(self.frames[name], "on_show"):
            self.frames[name].on_show()
        self._highlight_nav(name)

    def _highlight_nav(self, name: str):
        # nav 이름 매핑
        nav_map = {
            "dashboard": "dashboard",
            "task_list": "task_list",
            "task_form": "task_form_new",
            "task_detail": "task_list",
            "ai_panel": "ai_panel",
            "notion_sync": "notion_sync",
        }
        active = nav_map.get(name, name)
        self._current_nav = active
        for btn_name, btn in self.nav_buttons.items():
            btn.config(bg=C["sidebar_active"] if btn_name == active else C["sidebar"])

    def _nav_click(self, name: str):
        if name == "task_form_new":
            self._show_form(None)
        else:
            self.show_frame(name)

    def _show_detail(self, task_id: str):
        self.frames["task_detail"].load_task(task_id)
        self.show_frame("task_detail")

    def _show_form(self, task_id: str | None = None):
        self.frames["task_form"].set_mode(task_id)
        self.show_frame("task_form")

    # ═══════════════════════════════════════════════════════════════
    #  실행
    # ═══════════════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()
