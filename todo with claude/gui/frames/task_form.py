"""태스크 생성/수정 폼 프레임."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from gui.constants import (
    C, FONT_BODY, FONT_HEADING, FONT_TITLE,
    STATUS_KR, STATUS_EN, PRIORITY_KR, PRIORITY_EN,
)


class TaskFormFrame(tk.Frame):
    def __init__(self, parent, api, set_status, go_back, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.api = api
        self.set_status = set_status
        self.go_back = go_back  # callback: 폼 닫고 목록으로
        self._edit_id: str | None = None
        self._build()

    # ── UI 구성 ───────────────────────────────────────────────────

    def _build(self):
        # 헤더
        header = tk.Frame(self, bg=C["bg"])
        header.pack(fill=tk.X, padx=24, pady=(24, 8))
        ttk.Button(header, text="< 뒤로", command=self.go_back).pack(side=tk.LEFT)
        self.header_label = tk.Label(header, text="새 태스크", font=FONT_TITLE, bg=C["bg"], fg=C["text"])
        self.header_label.pack(side=tk.LEFT, padx=16)

        # 폼 카드
        card = tk.Frame(self, bg=C["card"], bd=1, relief=tk.SOLID)
        card.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)

        form = tk.Frame(card, bg=C["card"])
        form.pack(padx=24, pady=16, fill=tk.BOTH, expand=True)

        row = 0

        # 제목
        tk.Label(form, text="제목 *", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="w", pady=8)
        self.title_var = tk.StringVar()
        tk.Entry(form, textvariable=self.title_var, font=FONT_BODY, width=50).grid(row=row, column=1, sticky="ew", pady=8, padx=8)
        row += 1

        # 설명
        tk.Label(form, text="설명", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="nw", pady=8)
        self.desc_text = tk.Text(form, font=FONT_BODY, width=50, height=4, wrap=tk.WORD)
        self.desc_text.grid(row=row, column=1, sticky="ew", pady=8, padx=8)
        row += 1

        # 상태
        tk.Label(form, text="상태", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="w", pady=8)
        self.status_var = tk.StringVar(value="할 일")
        status_values = [STATUS_KR[k] for k in ("todo", "in_progress", "done")]
        ttk.Combobox(form, textvariable=self.status_var, values=status_values, width=15, state="readonly").grid(row=row, column=1, sticky="w", pady=8, padx=8)
        row += 1

        # 우선순위
        tk.Label(form, text="우선순위", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="w", pady=8)
        self.priority_var = tk.StringVar(value="보통")
        priority_values = [PRIORITY_KR[k] for k in ("low", "medium", "high", "urgent")]
        ttk.Combobox(form, textvariable=self.priority_var, values=priority_values, width=15, state="readonly").grid(row=row, column=1, sticky="w", pady=8, padx=8)
        row += 1

        # 태그
        tk.Label(form, text="태그", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="w", pady=8)
        self.tags_var = tk.StringVar()
        e = tk.Entry(form, textvariable=self.tags_var, font=FONT_BODY, width=50)
        e.grid(row=row, column=1, sticky="ew", pady=8, padx=8)
        tk.Label(form, text="쉼표로 구분 (예: 업무, 개발)", font=("Helvetica", 10), bg=C["card"], fg=C["text_secondary"]).grid(row=row+1, column=1, sticky="w", padx=8)
        row += 2

        # 마감일
        tk.Label(form, text="마감일", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="w", pady=8)
        self.due_var = tk.StringVar()
        e2 = tk.Entry(form, textvariable=self.due_var, font=FONT_BODY, width=25)
        e2.grid(row=row, column=1, sticky="w", pady=8, padx=8)
        tk.Label(form, text="형식: YYYY-MM-DD HH:MM (선택)", font=("Helvetica", 10), bg=C["card"], fg=C["text_secondary"]).grid(row=row+1, column=1, sticky="w", padx=8)
        row += 2

        # 예상 소요 시간
        tk.Label(form, text="예상 소요(분)", font=FONT_HEADING, bg=C["card"], fg=C["text"]).grid(row=row, column=0, sticky="w", pady=8)
        self.duration_var = tk.StringVar()
        tk.Entry(form, textvariable=self.duration_var, font=FONT_BODY, width=10).grid(row=row, column=1, sticky="w", pady=8, padx=8)
        row += 1

        form.columnconfigure(1, weight=1)

        # 저장 버튼
        btn_frame = tk.Frame(card, bg=C["card"])
        btn_frame.pack(pady=16)
        self.save_btn = ttk.Button(btn_frame, text="저장", command=self._save)
        self.save_btn.pack()

    # ── 폼 세팅 ──────────────────────────────────────────────────

    def set_mode(self, task_id: str | None = None):
        """생성 모드(task_id=None) 또는 수정 모드."""
        self._edit_id = task_id
        self._clear_form()

        if task_id:
            self.header_label.config(text="태스크 수정")
            try:
                t = self.api.get_task(task_id)
                self.title_var.set(t.get("title", ""))
                self.desc_text.delete("1.0", tk.END)
                self.desc_text.insert("1.0", t.get("description") or "")
                self.status_var.set(STATUS_KR.get(t.get("status", "todo"), "할 일"))
                self.priority_var.set(PRIORITY_KR.get(t.get("priority", "medium"), "보통"))
                self.tags_var.set(", ".join(t.get("tags") or []))
                due = t.get("due_date") or ""
                self.due_var.set(due[:16].replace("T", " ") if due else "")
                dur = t.get("estimated_duration")
                self.duration_var.set(str(dur) if dur else "")
            except Exception as e:
                messagebox.showerror("오류", f"태스크 로드 실패: {e}")
        else:
            self.header_label.config(text="새 태스크")

    def _clear_form(self):
        self.title_var.set("")
        self.desc_text.delete("1.0", tk.END)
        self.status_var.set("할 일")
        self.priority_var.set("보통")
        self.tags_var.set("")
        self.due_var.set("")
        self.duration_var.set("")

    # ── 저장 ─────────────────────────────────────────────────────

    def _save(self):
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("입력 오류", "제목을 입력하세요.")
            return

        data: dict = {
            "title": title,
            "status": STATUS_EN.get(self.status_var.get(), "todo"),
            "priority": PRIORITY_EN.get(self.priority_var.get(), "medium"),
        }

        desc = self.desc_text.get("1.0", tk.END).strip()
        if desc:
            data["description"] = desc

        tags_str = self.tags_var.get().strip()
        if tags_str:
            data["tags"] = [t.strip() for t in tags_str.split(",") if t.strip()]

        due = self.due_var.get().strip()
        if due:
            # YYYY-MM-DD HH:MM → ISO format
            try:
                if len(due) == 16:
                    data["due_date"] = due.replace(" ", "T") + ":00Z"
                elif len(due) == 10:
                    data["due_date"] = due + "T00:00:00Z"
                else:
                    data["due_date"] = due
            except Exception:
                data["due_date"] = due

        dur = self.duration_var.get().strip()
        if dur:
            try:
                data["estimated_duration"] = int(dur)
            except ValueError:
                messagebox.showwarning("입력 오류", "예상 소요 시간은 숫자로 입력하세요.")
                return

        try:
            if self._edit_id:
                self.api.update_task(self._edit_id, data)
                self.set_status("태스크 수정 완료")
            else:
                self.api.create_task(data)
                self.set_status("태스크 생성 완료")
            self.go_back()
        except Exception as e:
            messagebox.showerror("오류", f"저장 실패: {e}")

    def on_show(self):
        pass  # set_mode에서 처리
