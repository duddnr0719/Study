"""대시보드 프레임: 태스크 통계 요약."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.constants import C, FONT_BODY, FONT_HEADING, FONT_TITLE, STATUS_KR, PRIORITY_KR


class DashboardFrame(tk.Frame):
    def __init__(self, parent, api, set_status, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.api = api
        self.set_status = set_status
        self._build()

    # ── UI 구성 ───────────────────────────────────────────────────

    def _build(self):
        # 헤더
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill=tk.X, padx=24, pady=(24, 8))
        tk.Label(header, text="대시보드", font=FONT_TITLE, bg=C["bg"], fg=C["text"]).pack(side=tk.LEFT)
        ttk.Button(header, text="새로고침", command=self.on_show).pack(side=tk.RIGHT)

        # 상단 요약 카드 줄
        self.summary_frame = tk.Frame(self, bg=C["bg"])
        self.summary_frame.pack(fill=tk.X, padx=24, pady=8)

        # 상태별 / 우선순위별 카드
        mid = tk.Frame(self, bg=C["bg"])
        mid.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        self.status_frame = self._make_card(mid, "상태별", 0, 0)
        self.priority_frame = self._make_card(mid, "우선순위별", 0, 1)

    def _make_card(self, parent, title, row, col):
        card = tk.LabelFrame(
            parent, text=f"  {title}  ", font=FONT_HEADING,
            bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID,
        )
        card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)
        return card

    def _summary_card(self, parent, label, value, color=C["primary"]):
        f = tk.Frame(parent, bg=C["card"], bd=1, relief=tk.SOLID, padx=20, pady=12)
        f.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=6)
        tk.Label(f, text=str(value), font=("Helvetica", 28, "bold"), bg=C["card"], fg=color).pack()
        tk.Label(f, text=label, font=FONT_BODY, bg=C["card"], fg=C["text_secondary"]).pack()

    # ── 데이터 로드 ──────────────────────────────────────────────

    def on_show(self):
        try:
            stats = self.api.get_stats()
        except Exception as e:
            self.set_status(f"통계 로드 실패: {e}")
            return

        # 요약 카드 초기화 후 재구성
        for w in self.summary_frame.winfo_children():
            w.destroy()

        self._summary_card(self.summary_frame, "전체 태스크", stats["total"])
        self._summary_card(self.summary_frame, "완료율", f"{stats['completion_rate']}%", C["success"])
        self._summary_card(self.summary_frame, "오늘 완료", stats["completed_today"], C["success"])
        self._summary_card(self.summary_frame, "마감 초과", stats["overdue"], C["danger"])

        # 상태별
        for w in self.status_frame.winfo_children():
            w.destroy()
        for eng, cnt in stats.get("by_status", {}).items():
            kr = STATUS_KR.get(eng, eng)
            row = tk.Frame(self.status_frame, bg=C["card"])
            row.pack(fill=tk.X, padx=16, pady=4)
            tk.Label(row, text=kr, font=FONT_BODY, bg=C["card"], fg=C["text"], width=10, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=str(cnt), font=FONT_HEADING, bg=C["card"], fg=C["primary"]).pack(side=tk.RIGHT)

        # 우선순위별
        for w in self.priority_frame.winfo_children():
            w.destroy()
        for eng, cnt in stats.get("by_priority", {}).items():
            kr = PRIORITY_KR.get(eng, eng)
            row = tk.Frame(self.priority_frame, bg=C["card"])
            row.pack(fill=tk.X, padx=16, pady=4)
            tk.Label(row, text=kr, font=FONT_BODY, bg=C["card"], fg=C["text"], width=10, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=str(cnt), font=FONT_HEADING, bg=C["card"], fg=C["primary"]).pack(side=tk.RIGHT)

        self.set_status("대시보드 새로고침 완료")
