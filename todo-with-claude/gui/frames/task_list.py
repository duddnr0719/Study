"""태스크 목록 프레임: Treeview + 필터/검색/정렬."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from gui.constants import (
    C, FONT_BODY, FONT_HEADING, FONT_SMALL, FONT_TITLE,
    STATUS_KR, STATUS_EN, STATUS_LIST_KR,
    PRIORITY_KR, PRIORITY_EN, PRIORITY_LIST_KR,
    SORT_OPTIONS, SORT_DIR,
)


class TaskListFrame(tk.Frame):
    def __init__(self, parent, api, set_status, show_detail, show_form, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.api = api
        self.set_status = set_status
        self.show_detail = show_detail  # callback(task_id)
        self.show_form = show_form      # callback(task_id=None for new)
        self._tasks: list[dict] = []
        self._build()

    # ── UI 구성 ───────────────────────────────────────────────────

    def _build(self):
        # 헤더
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill=tk.X, padx=24, pady=(24, 8))
        tk.Label(header, text="태스크 목록", font=FONT_TITLE, bg=C["bg"], fg=C["text"]).pack(side=tk.LEFT)
        ttk.Button(header, text="+ 새 태스크", command=lambda: self.show_form()).pack(side=tk.RIGHT)

        # 필터 바
        fbar = tk.Frame(self, bg=C["card"], bd=1, relief=tk.SOLID)
        fbar.pack(fill=tk.X, padx=24, pady=4)

        # 검색
        tk.Label(fbar, text="검색:", font=FONT_SMALL, bg=C["card"]).pack(side=tk.LEFT, padx=(12, 4), pady=8)
        self.search_var = tk.StringVar()
        tk.Entry(fbar, textvariable=self.search_var, width=18, font=FONT_SMALL).pack(side=tk.LEFT, padx=4)

        # 상태 필터
        tk.Label(fbar, text="상태:", font=FONT_SMALL, bg=C["card"]).pack(side=tk.LEFT, padx=(12, 4))
        self.status_var = tk.StringVar(value="전체")
        ttk.Combobox(fbar, textvariable=self.status_var, values=STATUS_LIST_KR, width=8, state="readonly").pack(side=tk.LEFT, padx=4)

        # 우선순위 필터
        tk.Label(fbar, text="우선순위:", font=FONT_SMALL, bg=C["card"]).pack(side=tk.LEFT, padx=(12, 4))
        self.priority_var = tk.StringVar(value="전체")
        ttk.Combobox(fbar, textvariable=self.priority_var, values=PRIORITY_LIST_KR, width=8, state="readonly").pack(side=tk.LEFT, padx=4)

        # 태그
        tk.Label(fbar, text="태그:", font=FONT_SMALL, bg=C["card"]).pack(side=tk.LEFT, padx=(12, 4))
        self.tag_var = tk.StringVar()
        tk.Entry(fbar, textvariable=self.tag_var, width=10, font=FONT_SMALL).pack(side=tk.LEFT, padx=4)

        # 정렬
        tk.Label(fbar, text="정렬:", font=FONT_SMALL, bg=C["card"]).pack(side=tk.LEFT, padx=(12, 4))
        self.sort_var = tk.StringVar(value="생성일")
        ttk.Combobox(fbar, textvariable=self.sort_var, values=list(SORT_OPTIONS.keys()), width=7, state="readonly").pack(side=tk.LEFT, padx=4)

        self.dir_var = tk.StringVar(value="내림차순")
        ttk.Combobox(fbar, textvariable=self.dir_var, values=list(SORT_DIR.keys()), width=7, state="readonly").pack(side=tk.LEFT, padx=4)

        ttk.Button(fbar, text="조회", command=self.on_show).pack(side=tk.LEFT, padx=(12, 8), pady=8)

        # Treeview
        tree_frame = tk.Frame(self, bg=C["bg"])
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)

        cols = ("title", "status", "priority", "tags", "due_date")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("title", text="제목")
        self.tree.heading("status", text="상태")
        self.tree.heading("priority", text="우선순위")
        self.tree.heading("tags", text="태그")
        self.tree.heading("due_date", text="마감일")

        self.tree.column("title", width=300, minwidth=150)
        self.tree.column("status", width=80, minwidth=60, anchor="center")
        self.tree.column("priority", width=80, minwidth=60, anchor="center")
        self.tree.column("tags", width=150, minwidth=80)
        self.tree.column("due_date", width=140, minwidth=100, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_double_click)

        # 하단 버튼
        bottom = tk.Frame(self, bg=C["bg"])
        bottom.pack(fill=tk.X, padx=24, pady=(0, 16))
        ttk.Button(bottom, text="상세 보기", command=self._open_detail).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="수정", command=self._open_edit).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="삭제", command=self._delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="새로고침", command=self.on_show).pack(side=tk.RIGHT, padx=4)

    # ── 데이터 로드 ──────────────────────────────────────────────

    def on_show(self):
        params: dict = {
            "sort_by": SORT_OPTIONS.get(self.sort_var.get(), "created_at"),
            "sort_order": SORT_DIR.get(self.dir_var.get(), "desc"),
            "limit": 100,
        }
        s = self.status_var.get()
        if s != "전체":
            params["status"] = STATUS_EN.get(s)
        p = self.priority_var.get()
        if p != "전체":
            params["priority"] = PRIORITY_EN.get(p)
        search = self.search_var.get().strip()
        if search:
            params["search"] = search
        tag = self.tag_var.get().strip()
        if tag:
            params["tag"] = tag

        try:
            self._tasks = self.api.list_tasks(**params)
        except Exception as e:
            self.set_status(f"목록 로드 실패: {e}")
            return

        self._refresh_tree()
        self.set_status(f"태스크 {len(self._tasks)}건 조회 완료")

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for t in self._tasks:
            due = (t.get("due_date") or "")[:16].replace("T", " ")
            tags_str = ", ".join(t.get("tags") or [])
            self.tree.insert(
                "", tk.END,
                iid=t["id"],
                values=(
                    t["title"],
                    STATUS_KR.get(t["status"], t["status"]),
                    PRIORITY_KR.get(t["priority"], t["priority"]),
                    tags_str,
                    due,
                ),
            )

    # ── 이벤트 핸들러 ────────────────────────────────────────────

    def _selected_id(self) -> str | None:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _on_double_click(self, event=None):
        tid = self._selected_id()
        if tid:
            self.show_detail(tid)

    def _open_detail(self):
        tid = self._selected_id()
        if tid:
            self.show_detail(tid)
        else:
            messagebox.showinfo("알림", "태스크를 선택하세요.")

    def _open_edit(self):
        tid = self._selected_id()
        if tid:
            self.show_form(tid)
        else:
            messagebox.showinfo("알림", "태스크를 선택하세요.")

    def _delete_selected(self):
        tid = self._selected_id()
        if not tid:
            messagebox.showinfo("알림", "태스크를 선택하세요.")
            return
        if not messagebox.askyesno("삭제 확인", "선택한 태스크를 삭제하시겠습니까?"):
            return
        try:
            self.api.delete_task(tid)
            self.set_status("태스크 삭제 완료")
            self.on_show()
        except Exception as e:
            messagebox.showerror("오류", f"삭제 실패: {e}")
