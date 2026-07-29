"""UI 상수: 색상, 한국어 매핑, 폰트, 정렬 옵션."""

# ── 상태 매핑 ─────────────────────────────────────────────────────
STATUS_KR = {"todo": "할 일", "in_progress": "진행 중", "done": "완료"}
STATUS_EN = {v: k for k, v in STATUS_KR.items()}
STATUS_LIST_KR = ["전체", "할 일", "진행 중", "완료"]

# ── 우선순위 매핑 ────────────────────────────────────────────────
PRIORITY_KR = {"low": "낮음", "medium": "보통", "high": "높음", "urgent": "긴급"}
PRIORITY_EN = {v: k for k, v in PRIORITY_KR.items()}
PRIORITY_LIST_KR = ["전체", "낮음", "보통", "높음", "긴급"]

# ── 정렬 옵션 ────────────────────────────────────────────────────
SORT_OPTIONS = {"생성일": "created_at", "마감일": "due_date", "우선순위": "priority", "제목": "title"}
SORT_DIR = {"내림차순": "desc", "오름차순": "asc"}

# ── 색상 테마 ────────────────────────────────────────────────────
C = {
    "bg": "#f0f2f5",
    "sidebar": "#1e293b",
    "sidebar_hover": "#334155",
    "sidebar_active": "#3b82f6",
    "sidebar_text": "#e2e8f0",
    "card": "#ffffff",
    "border": "#e2e8f0",
    "text": "#1e293b",
    "text_secondary": "#64748b",
    "primary": "#3b82f6",
    "primary_hover": "#2563eb",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    # 우선순위 색상
    "p_low": "#94a3b8",
    "p_medium": "#3b82f6",
    "p_high": "#f59e0b",
    "p_urgent": "#ef4444",
    # 상태 색상
    "s_todo": "#64748b",
    "s_in_progress": "#3b82f6",
    "s_done": "#22c55e",
}

PRIORITY_COLOR = {"low": C["p_low"], "medium": C["p_medium"], "high": C["p_high"], "urgent": C["p_urgent"]}
STATUS_COLOR = {"todo": C["s_todo"], "in_progress": C["s_in_progress"], "done": C["s_done"]}

# ── 폰트 ─────────────────────────────────────────────────────────
FONT_TITLE = ("Helvetica", 18, "bold")
FONT_HEADING = ("Helvetica", 14, "bold")
FONT_BODY = ("Helvetica", 12)
FONT_SMALL = ("Helvetica", 10)
FONT_SIDEBAR = ("Helvetica", 13)
