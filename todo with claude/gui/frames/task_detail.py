"""태스크 상세 보기 + 서브태스크 관리 프레임."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from gui.constants import C, FONT_BODY, FONT_HEADING, FONT_SMALL, FONT_TITLE, STATUS_KR, PRIORITY_KR, PRIORITY_COLOR, STATUS_COLOR


class TaskDetailFrame(tk.Frame):
    def __init__(self, parent, api, set_status, go_back, show_form, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.api = api
        self.set_status = set_status
        self.go_back = go_back
        self.show_form = show_form  # callback(task_id) → 수정 폼
        self._task_id: str | None = None
        self._task: dict = {}
        self._build()

    # ── UI 구성 ───────────────────────────────────────────────────

    def _build(self):
        # 헤더
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill=tk.X, padx=24, pady=(24, 8))
        ttk.Button(header, text="< 목록으로", command=self.go_back).pack(side=tk.LEFT)
        ttk.Button(header, text="수정", command=self._edit).pack(side=tk.RIGHT, padx=4)
        ttk.Button(header, text="삭제", command=self._delete).pack(side=tk.RIGHT, padx=4)

        # 스크롤 영역
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=C["bg"])
        self.scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=24, pady=8)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 마우스 휠 스크롤
        def _on_mousewheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120 or (-1 if event.num == 4 else 1)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def load_task(self, task_id: str):
        self._task_id = task_id
        try:
            self._task = self.api.get_task(task_id)
        except Exception as e:
            self.set_status(f"태스크 로드 실패: {e}")
            return
        self._render()

    def _render(self):
        # 기존 내용 제거
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        t = self._task
        container = self.scroll_frame

        # 제목
        tk.Label(container, text=t.get("title", ""), font=FONT_TITLE, bg=C["bg"], fg=C["text"], wraplength=600, anchor="w", justify="left").pack(fill=tk.X, pady=(8, 4))

        # 상태 + 우선순위 배지
        badge_frame = tk.Frame(container, bg=C["bg"])
        badge_frame.pack(fill=tk.X, pady=4)

        status = t.get("status", "todo")
        s_color = STATUS_COLOR.get(status, C["text_secondary"])
        tk.Label(badge_frame, text=f" {STATUS_KR.get(status, status)} ", font=FONT_SMALL, bg=s_color, fg="white", padx=8, pady=2).pack(side=tk.LEFT, padx=(0, 8))

        priority = t.get("priority", "medium")
        p_color = PRIORITY_COLOR.get(priority, C["text_secondary"])
        tk.Label(badge_frame, text=f" {PRIORITY_KR.get(priority, priority)} ", font=FONT_SMALL, bg=p_color, fg="white", padx=8, pady=2).pack(side=tk.LEFT)

        # 정보 카드
        info = tk.LabelFrame(container, text="  상세 정보  ", font=FONT_HEADING, bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID)
        info.pack(fill=tk.X, pady=8)

        fields = [
            ("설명", t.get("description") or "(없음)"),
            ("태그", ", ".join(t.get("tags") or []) or "(없음)"),
            ("마감일", (t.get("due_date") or "")[:16].replace("T", " ") or "(없음)"),
            ("예상 소요", f"{t['estimated_duration']}분" if t.get("estimated_duration") else "(없음)"),
            ("AI 제안", t.get("ai_suggestion") or "(없음)"),
            ("Notion ID", t.get("notion_page_id") or "(동기화 안 됨)"),
            ("생성일", (t.get("created_at") or "")[:19].replace("T", " ")),
            ("수정일", (t.get("updated_at") or "")[:19].replace("T", " ")),
        ]
        for label, value in fields:
            row = tk.Frame(info, bg=C["card"])
            row.pack(fill=tk.X, padx=16, pady=3)
            tk.Label(row, text=f"{label}:", font=FONT_BODY, bg=C["card"], fg=C["text_secondary"], width=12, anchor="w").pack(side=tk.LEFT)
            tk.Label(row, text=str(value), font=FONT_BODY, bg=C["card"], fg=C["text"], wraplength=450, anchor="w", justify="left").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── 서브태스크 ────────────────────────────────────────────
        sub_frame = tk.LabelFrame(container, text="  서브태스크  ", font=FONT_HEADING, bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID)
        sub_frame.pack(fill=tk.X, pady=8)

        subtasks = t.get("subtasks") or []
        if not subtasks:
            tk.Label(sub_frame, text="서브태스크가 없습니다.", font=FONT_BODY, bg=C["card"], fg=C["text_secondary"]).pack(padx=16, pady=8)

        for st in subtasks:
            self._render_subtask(sub_frame, st)

        # 서브태스크 추가 버튼
        ttk.Button(sub_frame, text="+ 서브태스크 추가", command=self._add_subtask).pack(padx=16, pady=8)

    def _render_subtask(self, parent, st):
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill=tk.X, padx=16, pady=2)

        var = tk.BooleanVar(value=st.get("is_completed", False))
        cb = tk.Checkbutton(
            row, variable=var, bg=C["card"], activebackground=C["card"],
            command=lambda sid=st["id"], v=var: self._toggle_subtask(sid, v.get()),
        )
        cb.pack(side=tk.LEFT)

        title_text = st.get("title", "")
        lbl = tk.Label(row, text=title_text, font=FONT_BODY, bg=C["card"], fg=C["text"])
        if st.get("is_completed"):
            lbl.config(fg=C["text_secondary"])
        lbl.pack(side=tk.LEFT, padx=4)

        ttk.Button(row, text="삭제", command=lambda sid=st["id"]: self._delete_subtask(sid)).pack(side=tk.RIGHT, padx=4)

    # ── 서브태스크 동작 ──────────────────────────────────────────

    def _add_subtask(self):
        title = simpledialog.askstring("서브태스크 추가", "서브태스크 제목:", parent=self)
        if not title or not title.strip():
            return
        try:
            self.api.create_subtask(self._task_id, {"title": title.strip()})
            self.set_status("서브태스크 추가 완료")
            self.load_task(self._task_id)
        except Exception as e:
            messagebox.showerror("오류", f"추가 실패: {e}")

    def _toggle_subtask(self, subtask_id: str, completed: bool):
        try:
            self.api.update_subtask(self._task_id, subtask_id, {"is_completed": completed})
            self.set_status(f"서브태스크 {'완료' if completed else '미완료'}로 변경")
        except Exception as e:
            messagebox.showerror("오류", f"수정 실패: {e}")

    def _delete_subtask(self, subtask_id: str):
        if not messagebox.askyesno("확인", "서브태스크를 삭제하시겠습니까?"):
            return
        try:
            self.api.delete_subtask(self._task_id, subtask_id)
            self.set_status("서브태스크 삭제 완료")
            self.load_task(self._task_id)
        except Exception as e:
            messagebox.showerror("오류", f"삭제 실패: {e}")

    # ── 태스크 동작 ──────────────────────────────────────────────

    def _edit(self):
        if self._task_id:
            self.show_form(self._task_id)

    def _delete(self):
        if not messagebox.askyesno("삭제 확인", "이 태스크를 삭제하시겠습니까?\n(서브태스크도 함께 삭제됩니다)"):
            return
        try:
            self.api.delete_task(self._task_id)
            self.set_status("태스크 삭제 완료")
            self.go_back()
        except Exception as e:
            messagebox.showerror("오류", f"삭제 실패: {e}")

    def on_show(self):
        if self._task_id:
            self.load_task(self._task_id)
