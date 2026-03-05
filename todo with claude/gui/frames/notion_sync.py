"""Notion 동기화 프레임."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from gui.constants import C, FONT_BODY, FONT_HEADING, FONT_TITLE


class NotionSyncFrame(tk.Frame):
    def __init__(self, parent, api, set_status, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.api = api
        self.set_status = set_status
        self._build()

    def _build(self):
        # 헤더
        tk.Label(self, text="Notion 동기화", font=FONT_TITLE, bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=24, pady=(24, 8))

        # 동기화 버튼 카드
        btn_card = tk.LabelFrame(self, text="  동기화 작업  ", font=FONT_HEADING, bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID)
        btn_card.pack(fill=tk.X, padx=24, pady=8)

        actions = [
            ("미완료 태스크 전체 → Notion", "백엔드의 미완료 태스크를 모두 Notion에 동기화합니다.", self._sync_all),
            ("Notion → 백엔드 가져오기", "Notion DB의 태스크를 백엔드로 가져옵니다.", self._import_notion),
        ]
        for label, desc, cmd in actions:
            row = tk.Frame(btn_card, bg=C["card"])
            row.pack(fill=tk.X, padx=16, pady=6)
            ttk.Button(row, text=label, command=cmd, width=30).pack(side=tk.LEFT)
            tk.Label(row, text=desc, font=("Helvetica", 10), bg=C["card"], fg=C["text_secondary"]).pack(side=tk.LEFT, padx=12)

        # 단일 동기화
        single_frame = tk.Frame(btn_card, bg=C["card"])
        single_frame.pack(fill=tk.X, padx=16, pady=6)
        ttk.Button(single_frame, text="단일 태스크 동기화", command=self._sync_single, width=30).pack(side=tk.LEFT)
        self.task_id_var = tk.StringVar()
        tk.Entry(single_frame, textvariable=self.task_id_var, font=("Helvetica", 10), width=40).pack(side=tk.LEFT, padx=8)
        tk.Label(single_frame, text="태스크 ID 입력", font=("Helvetica", 10), bg=C["card"], fg=C["text_secondary"]).pack(side=tk.LEFT)

        # 진행 표시
        self.progress_label = tk.Label(btn_card, text="", font=FONT_BODY, bg=C["card"], fg=C["primary"])
        self.progress_label.pack(padx=16, pady=4)

        # 로그 영역
        log_card = tk.LabelFrame(self, text="  동기화 로그  ", font=FONT_HEADING, bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID)
        log_card.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)

        self.log_text = tk.Text(log_card, font=("Courier", 11), wrap=tk.WORD, state=tk.DISABLED, bg="#f8fafc")
        vsb = ttk.Scrollbar(log_card, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=vsb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _log(self, msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{now}] {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _set_progress(self, msg: str):
        self.progress_label.config(text=msg)

    # ── 전체 동기화 ──────────────────────────────────────────────

    def _sync_all(self):
        self._set_progress("전체 동기화 중...")
        self._log("전체 동기화 시작...")

        def worker():
            try:
                result = self.api.sync_all()
                self.after(0, self._sync_all_done, result)
            except Exception as e:
                self.after(0, self._sync_error, "전체 동기화", e)

        threading.Thread(target=worker, daemon=True).start()

    def _sync_all_done(self, result: list):
        self._set_progress("")
        count = len(result)
        self._log(f"전체 동기화 완료: {count}개 태스크 동기화됨")
        for t in result:
            self._log(f"  - \"{t.get('title')}\" → Notion: {t.get('notion_page_id', '?')[:12]}...")
        self.set_status(f"Notion 전체 동기화 완료 ({count}건)")

    # ── Notion에서 가져오기 ──────────────────────────────────────

    def _import_notion(self):
        self._set_progress("Notion에서 가져오는 중...")
        self._log("Notion → 백엔드 가져오기 시작...")

        def worker():
            try:
                result = self.api.import_from_notion()
                self.after(0, self._import_done, result)
            except Exception as e:
                self.after(0, self._sync_error, "Notion 가져오기", e)

        threading.Thread(target=worker, daemon=True).start()

    def _import_done(self, result: list):
        self._set_progress("")
        count = len(result)
        self._log(f"Notion 가져오기 완료: {count}개 태스크")
        for t in result:
            self._log(f"  - \"{t.get('title')}\" (상태: {t.get('status')})")
        self.set_status(f"Notion에서 {count}건 가져오기 완료")

    # ── 단일 동기화 ──────────────────────────────────────────────

    def _sync_single(self):
        task_id = self.task_id_var.get().strip()
        if not task_id:
            messagebox.showwarning("입력 필요", "동기화할 태스크 ID를 입력하세요.")
            return

        self._set_progress("단일 동기화 중...")
        self._log(f"단일 동기화 시작: {task_id[:12]}...")

        def worker():
            try:
                result = self.api.sync_task(task_id)
                self.after(0, self._single_done, result)
            except Exception as e:
                self.after(0, self._sync_error, "단일 동기화", e)

        threading.Thread(target=worker, daemon=True).start()

    def _single_done(self, result: dict):
        self._set_progress("")
        self._log(f"단일 동기화 완료: \"{result.get('title')}\" → Notion: {result.get('notion_page_id', '?')[:12]}...")
        self.set_status("단일 태스크 Notion 동기화 완료")

    # ── 공통 에러 핸들러 ─────────────────────────────────────────

    def _sync_error(self, action: str, error):
        self._set_progress("")
        self._log(f"[오류] {action} 실패: {error}")
        self.set_status(f"{action} 실패: {error}")

    def on_show(self):
        pass
