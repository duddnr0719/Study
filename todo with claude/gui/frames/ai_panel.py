"""AI 기능 프레임: 자연어 파싱 + AI 추천."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from gui.constants import C, FONT_BODY, FONT_HEADING, FONT_TITLE


class AIPanelFrame(tk.Frame):
    def __init__(self, parent, api, set_status, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self.api = api
        self.set_status = set_status
        self._build()

    def _build(self):
        # 헤더
        tk.Label(self, text="AI 도구", font=FONT_TITLE, bg=C["bg"], fg=C["text"]).pack(anchor="w", padx=24, pady=(24, 8))

        # ── 자연어 파싱 섹션 ──────────────────────────────────────
        parse_card = tk.LabelFrame(self, text="  자연어로 태스크 만들기  ", font=FONT_HEADING, bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID)
        parse_card.pack(fill=tk.X, padx=24, pady=8)

        tk.Label(parse_card, text="자연어를 입력하면 AI가 자동으로 태스크를 생성합니다.", font=("Helvetica", 10), bg=C["card"], fg=C["text_secondary"]).pack(anchor="w", padx=16, pady=(8, 4))

        self.parse_input = tk.Text(parse_card, font=FONT_BODY, height=3, wrap=tk.WORD)
        self.parse_input.pack(fill=tk.X, padx=16, pady=4)
        self.parse_input.insert("1.0", "예: 내일까지 분기 보고서 작성해야 함, 급함")

        btn_frame = tk.Frame(parse_card, bg=C["card"])
        btn_frame.pack(fill=tk.X, padx=16, pady=4)
        self.parse_btn = ttk.Button(btn_frame, text="AI 파싱하여 생성", command=self._do_parse)
        self.parse_btn.pack(side=tk.LEFT)
        self.parse_spinner = tk.Label(btn_frame, text="", font=FONT_BODY, bg=C["card"], fg=C["primary"])
        self.parse_spinner.pack(side=tk.LEFT, padx=8)

        tk.Label(parse_card, text="생성 결과:", font=FONT_HEADING, bg=C["card"], fg=C["text"]).pack(anchor="w", padx=16, pady=(8, 0))
        self.parse_result = tk.Text(parse_card, font=FONT_BODY, height=6, wrap=tk.WORD, state=tk.DISABLED, bg="#f8fafc")
        self.parse_result.pack(fill=tk.X, padx=16, pady=(4, 12))

        # ── AI 추천 섹션 ─────────────────────────────────────────
        suggest_card = tk.LabelFrame(self, text="  AI 추천 분석  ", font=FONT_HEADING, bg=C["card"], fg=C["text"], bd=1, relief=tk.SOLID)
        suggest_card.pack(fill=tk.BOTH, expand=True, padx=24, pady=8)

        tk.Label(suggest_card, text="미완료 태스크를 분석하여 우선순위와 일정을 추천합니다.", font=("Helvetica", 10), bg=C["card"], fg=C["text_secondary"]).pack(anchor="w", padx=16, pady=(8, 4))

        btn_frame2 = tk.Frame(suggest_card, bg=C["card"])
        btn_frame2.pack(fill=tk.X, padx=16, pady=4)
        self.suggest_btn = ttk.Button(btn_frame2, text="AI 추천 받기", command=self._do_suggest)
        self.suggest_btn.pack(side=tk.LEFT)
        self.suggest_spinner = tk.Label(btn_frame2, text="", font=FONT_BODY, bg=C["card"], fg=C["primary"])
        self.suggest_spinner.pack(side=tk.LEFT, padx=8)

        self.suggest_result = tk.Text(suggest_card, font=FONT_BODY, wrap=tk.WORD, state=tk.DISABLED, bg="#f8fafc")
        self.suggest_result.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 12))

    # ── 자연어 파싱 ──────────────────────────────────────────────

    def _do_parse(self):
        text = self.parse_input.get("1.0", tk.END).strip()
        if not text or len(text) < 2:
            messagebox.showwarning("입력 오류", "2글자 이상 입력하세요.")
            return

        self.parse_btn.config(state=tk.DISABLED)
        self.parse_spinner.config(text="처리 중...")

        def worker():
            try:
                result = self.api.parse_natural_language(text)
                self.after(0, self._parse_done, result)
            except Exception as e:
                self.after(0, self._parse_error, e)

        threading.Thread(target=worker, daemon=True).start()

    def _parse_done(self, result: dict):
        self.parse_btn.config(state=tk.NORMAL)
        self.parse_spinner.config(text="")

        lines = [
            f"제목: {result.get('title', '')}",
            f"상태: {result.get('status', '')}",
            f"우선순위: {result.get('priority', '')}",
            f"태그: {', '.join(result.get('tags') or [])}",
            f"마감일: {(result.get('due_date') or '(없음)')[:16]}",
            f"예상 소요: {result.get('estimated_duration') or '(없음)'}분",
            f"AI 메모: {result.get('ai_suggestion') or ''}",
        ]
        self.parse_result.config(state=tk.NORMAL)
        self.parse_result.delete("1.0", tk.END)
        self.parse_result.insert("1.0", "\n".join(lines))
        self.parse_result.config(state=tk.DISABLED)
        self.set_status("AI 파싱 완료 — 태스크가 생성되었습니다")

    def _parse_error(self, error):
        self.parse_btn.config(state=tk.NORMAL)
        self.parse_spinner.config(text="")
        self.parse_result.config(state=tk.NORMAL)
        self.parse_result.delete("1.0", tk.END)
        self.parse_result.insert("1.0", f"오류: {error}")
        self.parse_result.config(state=tk.DISABLED)
        self.set_status(f"AI 파싱 실패: {error}")

    # ── AI 추천 ──────────────────────────────────────────────────

    def _do_suggest(self):
        self.suggest_btn.config(state=tk.DISABLED)
        self.suggest_spinner.config(text="분석 중...")

        def worker():
            try:
                result = self.api.get_ai_suggestions()
                self.after(0, self._suggest_done, result)
            except Exception as e:
                self.after(0, self._suggest_error, e)

        threading.Thread(target=worker, daemon=True).start()

    def _suggest_done(self, result: dict):
        self.suggest_btn.config(state=tk.NORMAL)
        self.suggest_spinner.config(text="")
        self.suggest_result.config(state=tk.NORMAL)
        self.suggest_result.delete("1.0", tk.END)
        self.suggest_result.insert("1.0", result.get("suggestion", "(결과 없음)"))
        self.suggest_result.config(state=tk.DISABLED)
        self.set_status("AI 추천 분석 완료")

    def _suggest_error(self, error):
        self.suggest_btn.config(state=tk.NORMAL)
        self.suggest_spinner.config(text="")
        self.suggest_result.config(state=tk.NORMAL)
        self.suggest_result.delete("1.0", tk.END)
        self.suggest_result.insert("1.0", f"오류: {error}\n\n(Anthropic API 키가 설정되어 있는지 확인하세요)")
        self.suggest_result.config(state=tk.DISABLED)
        self.set_status(f"AI 추천 실패: {error}")

    def on_show(self):
        pass
