"""
File Gateway - Slack ↔ 서버 공유폴더 파일 브릿지

사용법:
  파일 + "save <폴더경로>" : 파일을 첨부하고 메시지에 save를 입력하면 서버에 저장
  /save <폴더경로>         : 채널의 최근 파일을 서버에 저장
  /fetch <경로>            : 서버 파일/폴더를 Slack으로 전송 (폴더는 zip 압축)
  /ls <경로>               : 서버 폴더의 파일 목록 조회
  /cd <경로>               : 현재 디렉토리 이동 (.. 으로 상위 이동 가능)
  /pwd                     : 현재 디렉토리 확인
  /create <폴더명>         : 새 폴더 생성
"""

import os
import re
import json
import time
import uuid
import shutil
import zipfile
import logging
import tempfile
import itertools
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── 환경변수 ──
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
BASE_STORAGE_PATH = Path(os.environ.get("BASE_STORAGE_PATH", "./test_storage")).resolve()
STATE_FILE = Path(os.environ.get("STATE_FILE", "./state.json"))

PENDING_SAVE_TTL   = 600   # pending_saves 만료 시간 (10분)
CLEANUP_INTERVAL   = 300   # 자동 cleanup 주기 (5분)
DOWNLOAD_TIMEOUT   = 30    # 파일 다운로드 타임아웃 (초)

# Rate limiting
FETCH_COOLDOWN     = 10    # /fetch 최소 간격 (초, 사용자당)
SAVE_COOLDOWN      = 3     # save 최소 간격 (초, 사용자당)
CMD_COOLDOWN       = 2     # 그 외 커맨드 최소 간격 (초, 사용자당)

# /fetch 크기 제한
MAX_ZIP_FILES      = 500   # zip 최대 파일 수
MAX_ZIP_SIZE_MB    = 500   # zip 최대 총 크기 (MB)

# /ls 메모리 제한
MAX_LS_ITEMS       = 200   # iterdir() 최대 항목 수 (정렬 전 슬라이스)

# 허용되는 폴더명 패턴 (영문, 숫자, 한글, 일부 특수문자만)
SAFE_FOLDER_NAME_RE = re.compile(r'^[a-zA-Z0-9가-힣._\-]+$')

# 버튼 액션 user_id 불일치 sentinel
_UNAUTHORIZED = object()

app = App(token=SLACK_BOT_TOKEN)
client = WebClient(token=SLACK_BOT_TOKEN)

BOT_USER_ID = None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  락 & 공유 상태
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# B1: 모든 공유 딕셔너리 접근을 단일 Lock 으로 보호
_data_lock = threading.Lock()

# user-scoped 디렉토리: "{channel_id}:{user_id}" → 현재 상대경로
channel_dirs: dict[str, str] = {}

# pending_saves: pending_id → 작업 정보
pending_saves: dict[str, dict] = {}

# B4: 현재 저장 진행 중인 실제 파일 경로 집합 (동일 파일 동시 저장 방지)
_in_progress_paths: set[str] = set()

# Rate limiting: "{user_id}:{cmd}" → 마지막 실행 시각
_rate_lock = threading.Lock()
_user_last_cmd: dict[str, float] = {}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Rate Limiting
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _check_rate_limit(user_id: str, cmd: str, cooldown: float) -> bool:
    """허용이면 True, 제한 중이면 False 반환."""
    key = f"{user_id}:{cmd}"
    now = time.time()
    with _rate_lock:
        last = _user_last_cmd.get(key, 0.0)
        if now - last < cooldown:
            return False
        _user_last_cmd[key] = now
        return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  상태 영속성 (JSON 파일)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_state():
    """시작 시 state.json 에서 상태 복원."""
    global channel_dirs, pending_saves
    if not STATE_FILE.exists():
        return
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        now = time.time()
        restored = {}
        for k, v in data.get("pending_saves", {}).items():
            if now - v.get("created_at", 0) < PENDING_SAVE_TTL:
                v["dest_dir"] = Path(v["dest_dir"])
                restored[k] = v
        with _data_lock:
            channel_dirs = data.get("channel_dirs", {})
            pending_saves = restored
        logger.info(f"상태 복원: channel_dirs={len(channel_dirs)}, pending_saves={len(restored)}")
    except Exception as e:
        logger.warning(f"상태 로드 실패 (초기화 상태로 시작): {e}")


def _save_state():
    """현재 상태를 state.json 에 저장.

    A3 fix:
    - 딕셔너리 스냅샷을 lock 안에서 읽고
    - 파일 I/O 는 lock 밖에서 수행 (I/O 중 lock 점유 최소화)
    - 원자적 rename (tmp → STATE_FILE) 으로 부분 기록 방지
    C4 fix:
    - 파일 권한을 600 으로 제한 (소유자만 읽기/쓰기)
    """
    with _data_lock:
        snapshot = {
            "channel_dirs": dict(channel_dirs),
            "pending_saves": {
                k: {**v, "dest_dir": str(v["dest_dir"])}
                for k, v in pending_saves.items()
            },
        }

    try:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)   # 원자적 rename
        try:
            os.chmod(STATE_FILE, 0o600)
        except OSError:
            pass  # Windows 등 지원 안 되는 환경 무시
    except Exception as e:
        logger.error(f"상태 저장 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  자동 cleanup 백그라운드 스레드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _cleanup_expired_locked() -> list[str]:
    """_data_lock 보유 중에 호출하는 내부 전용 cleanup.
    만료된 키 목록을 반환."""
    now = time.time()
    expired = [k for k, v in pending_saves.items() if now - v["created_at"] > PENDING_SAVE_TTL]
    for k in expired:
        pending_saves.pop(k, None)
    return expired


def cleanup_expired_pending():
    """만료된 pending_saves 항목 제거 (lock 자체 획득 버전)."""
    with _data_lock:
        expired = _cleanup_expired_locked()
    if expired:
        logger.info(f"만료된 pending_saves {len(expired)}건 정리")
        _save_state()


def _auto_cleanup_loop():
    """CLEANUP_INTERVAL 주기로 자동 cleanup 실행.
    B3 fix: 예외가 발생해도 스레드가 종료되지 않도록 try/except 추가."""
    while True:
        time.sleep(CLEANUP_INTERVAL)
        try:
            cleanup_expired_pending()
        except Exception as e:
            logger.error(f"자동 cleanup 오류 (스레드 계속 유지): {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  user-scoped 디렉토리 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _dir_key(channel_id: str, user_id: str) -> str:
    return f"{channel_id}:{user_id}"


def get_current_dir(channel_id: str, user_id: str) -> str:
    with _data_lock:
        return channel_dirs.get(_dir_key(channel_id, user_id), ".")


def set_current_dir(channel_id: str, user_id: str, path: str):
    with _data_lock:
        channel_dirs[_dir_key(channel_id, user_id)] = path
    _save_state()


def resolve_path(channel_id: str, user_id: str, user_input: str) -> str:
    """사용자 입력 경로를 현재 디렉토리 기준으로 해석."""
    user_input = user_input.strip()
    if not user_input:
        return get_current_dir(channel_id, user_id)
    if user_input.startswith("/"):
        return user_input.lstrip("/") or "."
    current = get_current_dir(channel_id, user_id)
    if current == ".":
        return user_input
    return f"{current}/{user_input}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  보안 유틸리티
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def safe_resolve(user_path: str) -> Path:
    """경로를 BASE_STORAGE_PATH 내부로 제한 (is_relative_to 로 symlink 우회 방지)."""
    target = (BASE_STORAGE_PATH / user_path).resolve()
    if not target.is_relative_to(BASE_STORAGE_PATH):
        raise ValueError("접근 불가: 공유폴더 범위를 벗어난 경로입니다.")
    return target


def validate_folder_name(name: str) -> bool:
    """폴더명 유효성 검사: 안전한 문자만 허용."""
    return bool(SAFE_FOLDER_NAME_RE.match(name)) and name not in (".", "..")


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def make_renamed_path(dest_dir: Path, filename: str) -> Path:
    """중복 시 타임스탬프를 붙인 새 경로 생성."""
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return dest_dir / f"{stem}_{timestamp}{suffix}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  파일 다운로드 (스트리밍, 타임아웃 적용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def download_file_to_temp(file_info: dict) -> str:
    """Slack 파일을 청크 단위로 임시 파일에 저장. 임시 파일 경로 반환."""
    req = urllib.request.Request(
        file_info["url_private"],
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
    )
    suffix = Path(file_info.get("name", "file")).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            while True:
                chunk = resp.read(1024 * 1024)  # 1MB 청크
                if not chunk:
                    break
                tmp.write(chunk)
        tmp.close()
        return tmp.name
    except Exception:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)
        raise


def move_temp_to_dest(tmp_path: str, dest: Path):
    """임시 파일을 최종 경로로 이동 (크로스 디바이스 대응)."""
    try:
        shutil.move(tmp_path, dest)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  중복 파일 처리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def send_duplicate_prompt(channel_id: str, filename: str, dest_path: str, pending_id: str):
    """중복 감지 시 선택 버튼 전송."""
    client.chat_postMessage(
        channel=channel_id,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":warning: *중복 파일 감지*\n"
                        f"`{dest_path}/{filename}` 이(가) 이미 존재합니다.\n"
                        f"어떻게 처리할까요?"
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "덮어쓰기"},
                        "style": "danger",
                        "action_id": "fg_overwrite",
                        "value": pending_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "새 이름으로 저장"},
                        "style": "primary",
                        "action_id": "fg_rename",
                        "value": pending_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "취소"},
                        "action_id": "fg_cancel",
                        "value": pending_id,
                    },
                ],
            },
        ],
    )


def process_files_with_duplicate_check(
    files: list, dest_dir: Path, dest_path: str, channel_id: str, user_id: str
) -> list[str]:
    """파일 목록을 처리하면서 중복 검사.

    B4 fix: _in_progress_paths 로 동일 경로 동시 저장 방지.
    lock 안에서 만료 cleanup + 중복 검사 + in_progress 등록을 원자적으로 수행.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for file_info in files:
        filename = file_info["name"]
        save_path = dest_dir / filename
        path_str = str(save_path)
        pending_id = None

        with _data_lock:
            # 현재 저장 중인 파일인지 확인
            if path_str in _in_progress_paths:
                results.append(f":x: `{filename}` 이미 저장 진행 중입니다. 잠시 후 다시 시도해주세요.")
                continue

            # 만료 cleanup (lock 보유 중 내부 버전 호출)
            _cleanup_expired_locked()

            is_duplicate = save_path.exists()

            if is_duplicate:
                pending_id = str(uuid.uuid4())
                pending_saves[pending_id] = {
                    "file_info": file_info,
                    "dest_dir": dest_dir,
                    "dest_path": dest_path,
                    "filename": filename,
                    "channel_id": channel_id,
                    "user_id": user_id,       # A1 fix: 요청자 user_id 기록
                    "created_at": time.time(),
                }
            else:
                # 먼저 in_progress 등록 후 lock 해제 → 다른 스레드가 exists() 체크해도 차단
                _in_progress_paths.add(path_str)

        if is_duplicate:
            _save_state()
            send_duplicate_prompt(channel_id, filename, dest_path, pending_id)
            results.append(f":hourglass_flowing_sand: `{filename}` — 중복 파일, 처리 방식을 선택해주세요.")
        else:
            try:
                tmp_path = download_file_to_temp(file_info)
                move_temp_to_dest(tmp_path, save_path)
                results.append(f":white_check_mark: `{filename}` → `{dest_path}/{filename}`")
                logger.info(f"저장 완료: {save_path}")
            except Exception as e:
                logger.error(f"파일 저장 실패 ({filename}): {e}")
                results.append(f":x: `{filename}` 저장 실패")
            finally:
                with _data_lock:
                    _in_progress_paths.discard(path_str)

    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션 공통 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_pending(body: dict) -> tuple[str, object, str, str]:
    """pending_saves 에서 작업 조회.

    A1 fix: 클릭한 사용자가 요청자(user_id)와 다르면 _UNAUTHORIZED sentinel 반환.
    반환: (pending_id, pending | None | _UNAUTHORIZED, channel_id, message_ts)
    """
    pending_id = body["actions"][0]["value"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    actor_user_id = body["user"]["id"]

    # 만료 항목 정리 (lock 자체 획득 버전; 아래 with _data_lock 과 중첩 없음)
    cleanup_expired_pending()

    with _data_lock:
        pending = pending_saves.get(pending_id)
        if pending is None:
            return pending_id, None, channel_id, message_ts
        # A1: 버튼 클릭자와 save 요청자가 다르면 차단
        if pending["user_id"] != actor_user_id:
            return pending_id, _UNAUTHORIZED, channel_id, message_ts
        del pending_saves[pending_id]

    _save_state()
    return pending_id, pending, channel_id, message_ts


def _handle_unauthorized(client, channel_id: str, message_ts: str):
    """권한 없는 버튼 클릭 응답 (메시지는 수정하지 않고 ephemeral 처리)."""
    # chat_update 대신 그냥 로그만 남김 (메시지를 타인이 변경하지 못하게)
    logger.warning(f"권한 없는 버튼 클릭: channel={channel_id}, ts={message_ts}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션: 덮어쓰기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.action("fg_overwrite")
def action_overwrite(ack, body, client):
    ack()
    _, pending, channel_id, message_ts = _get_pending(body)

    if pending is _UNAUTHORIZED:
        _handle_unauthorized(client, channel_id, message_ts)
        return

    if not pending:
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=":x: 처리 시간이 초과되었거나 이미 처리된 작업입니다.", blocks=[]
        )
        return

    filename = pending["filename"]
    dest_dir = pending["dest_dir"]
    dest_path = pending["dest_path"]

    try:
        tmp_path = download_file_to_temp(pending["file_info"])
        move_temp_to_dest(tmp_path, dest_dir / filename)
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":white_check_mark: `{filename}` → `{dest_path}/{filename}` (덮어쓰기 완료)",
            blocks=[],
        )
        logger.info(f"덮어쓰기 완료: {dest_dir / filename}")
    except Exception as e:
        logger.error(f"덮어쓰기 실패 ({filename}): {e}")
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":x: `{filename}` 덮어쓰기 실패", blocks=[]
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션: 새 이름으로 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.action("fg_rename")
def action_rename(ack, body, client):
    ack()
    _, pending, channel_id, message_ts = _get_pending(body)

    if pending is _UNAUTHORIZED:
        _handle_unauthorized(client, channel_id, message_ts)
        return

    if not pending:
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=":x: 처리 시간이 초과되었거나 이미 처리된 작업입니다.", blocks=[]
        )
        return

    filename = pending["filename"]
    dest_dir = pending["dest_dir"]
    dest_path = pending["dest_path"]

    try:
        tmp_path = download_file_to_temp(pending["file_info"])
        new_path = make_renamed_path(dest_dir, filename)
        move_temp_to_dest(tmp_path, new_path)
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":white_check_mark: `{filename}` → `{dest_path}/{new_path.name}` (새 이름으로 저장)",
            blocks=[],
        )
        logger.info(f"새 이름 저장 완료: {new_path}")
    except Exception as e:
        logger.error(f"새 이름 저장 실패 ({filename}): {e}")
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":x: `{filename}` 저장 실패", blocks=[]
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션: 취소
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.action("fg_cancel")
def action_cancel(ack, body, client):
    ack()
    _, pending, channel_id, message_ts = _get_pending(body)

    if pending is _UNAUTHORIZED:
        _handle_unauthorized(client, channel_id, message_ts)
        return

    filename = pending["filename"] if pending else "파일"
    client.chat_update(
        channel=channel_id, ts=message_ts,
        text=f":no_entry_sign: `{filename}` 저장을 취소했습니다.",
        blocks=[],
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  메시지 이벤트: 파일 + "save <경로>" → 서버 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.event("message")
def handle_message_save(event, say):
    if event.get("user") == BOT_USER_ID or event.get("bot_id"):
        return

    text = event.get("text", "").strip()
    files = event.get("files", [])
    channel_id = event.get("channel", "")
    user_id = event.get("user", "")

    match = re.match(r"^save(?:\s+(.+))?$", text, re.IGNORECASE)
    if not match or not files:
        return

    # C2 fix: rate limiting
    if not _check_rate_limit(user_id, "save", SAVE_COOLDOWN):
        say(":hourglass: `save` 명령은 잠시 후 다시 시도해주세요.")
        return

    user_input = (match.group(1) or "").strip()
    dest_path = resolve_path(channel_id, user_id, user_input)

    try:
        dest_dir = safe_resolve(dest_path)
    except ValueError:
        say(":x: 접근할 수 없는 경로입니다.")
        return

    valid_files = [f for f in files if f.get("mode") != "tombstone"]
    if not valid_files:
        say(":warning: 저장할 수 있는 파일이 없습니다.")
        return

    results = process_files_with_duplicate_check(valid_files, dest_dir, dest_path, channel_id, user_id)
    say("\n".join(results))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /cd <경로> — 디렉토리 이동 (user-scoped)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command("/cd")
def handle_cd(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    if not _check_rate_limit(user_id, "cd", CMD_COOLDOWN):
        respond(":hourglass: 잠시 후 다시 시도해주세요.")
        return

    user_input = command["text"].strip()

    if not user_input:
        set_current_dir(channel_id, user_id, ".")
        respond(":open_file_folder: 루트 디렉토리로 이동했습니다: `/`")
        return

    new_path = resolve_path(channel_id, user_id, user_input)

    try:
        resolved = (BASE_STORAGE_PATH / new_path).resolve()
        if not resolved.is_relative_to(BASE_STORAGE_PATH):
            respond(":x: 공유폴더 범위를 벗어날 수 없습니다.")
            return
        if not resolved.exists():
            respond(":x: 경로를 찾을 수 없습니다.")
            return
        if not resolved.is_dir():
            respond(":x: 디렉토리가 아닙니다.")
            return
    except Exception:
        respond(":x: 경로 처리 중 오류가 발생했습니다.")
        return

    relative = str(resolved.relative_to(BASE_STORAGE_PATH))
    display = "/" if relative == "." else f"/{relative}"
    set_current_dir(channel_id, user_id, relative)
    respond(f":open_file_folder: `{display}` 로 이동했습니다.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /pwd — 현재 디렉토리 확인 (user-scoped)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command("/pwd")
def handle_pwd(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_id = command["user_id"]
    current = get_current_dir(channel_id, user_id)
    display = "/" if current == "." else f"/{current}"
    respond(f":round_pushpin: 현재 디렉토리: `{display}`")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /ls <경로> — 폴더 목록 조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command("/ls")
def handle_ls(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    if not _check_rate_limit(user_id, "ls", CMD_COOLDOWN):
        respond(":hourglass: 잠시 후 다시 시도해주세요.")
        return

    user_path = resolve_path(channel_id, user_id, command["text"])

    try:
        target = safe_resolve(user_path)
    except ValueError:
        respond(":x: 접근할 수 없는 경로입니다.")
        return

    if not target.exists():
        respond(":x: 경로를 찾을 수 없습니다.")
        return

    if not target.is_dir():
        try:
            size = format_size(target.stat().st_size)
        except OSError:
            size = "알 수 없음"
        respond(f":page_facing_up: `{target.name}` ({size})")
        return

    # C3 fix: iterdir() 를 MAX_LS_ITEMS+1 개만 읽고 정렬 (전체 로드 방지)
    try:
        raw = list(itertools.islice(target.iterdir(), MAX_LS_ITEMS + 1))
    except OSError:
        respond(":x: 폴더 목록을 읽는 중 오류가 발생했습니다.")
        return

    truncated = len(raw) > MAX_LS_ITEMS
    items = sorted(raw[:MAX_LS_ITEMS], key=lambda p: (p.is_file(), p.name))

    display_path = "/" if user_path == "." else f"/{user_path}"

    if not items:
        respond(f":open_file_folder: `{display_path}` — 빈 폴더입니다.")
        return

    lines = [f":open_file_folder: *`{display_path}`* 목록:\n"]
    for item in items:
        if item.is_symlink():
            lines.append(f"  :link: `{item.name}` (symlink)")
        elif item.is_dir():
            lines.append(f"  :file_folder: `{item.name}/`")
        else:
            try:
                size = format_size(item.stat().st_size)
            except OSError:
                size = "?"
            lines.append(f"  :page_facing_up: `{item.name}` ({size})")

    if truncated:
        lines.append(f"\n  … (처음 {MAX_LS_ITEMS}개만 표시, 실제 더 많은 항목이 있을 수 있음)")

    message = "\n".join(lines)
    if len(message) > 3800:
        message = "\n".join(lines[:51]) + f"\n  … (메시지 길이 초과로 일부만 표시)"

    respond(message)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /save <폴더경로> — 채널 최근 파일을 서버에 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command("/save")
def handle_save(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    # C2 fix: rate limiting
    if not _check_rate_limit(user_id, "save", SAVE_COOLDOWN):
        respond(":hourglass: `save` 명령은 잠시 후 다시 시도해주세요.")
        return

    dest_path = resolve_path(channel_id, user_id, command["text"])

    try:
        dest_dir = safe_resolve(dest_path)
    except ValueError:
        respond(":x: 접근할 수 없는 경로입니다.")
        return

    try:
        result = client.conversations_history(channel=channel_id, limit=10)
    except Exception:
        respond(":x: 채널 히스토리 조회에 실패했습니다.")
        return

    files_found = []
    for msg in result.get("messages", []):
        if msg.get("user") == BOT_USER_ID or msg.get("bot_id"):
            continue
        # A2 fix: 명령 실행자 본인이 올린 파일만 저장
        if msg.get("user") != user_id:
            continue
        if "files" in msg:
            for f in msg["files"]:
                if f.get("mode") != "tombstone":
                    files_found.append(f)
            if files_found:
                break

    if not files_found:
        respond(
            ":warning: 저장할 파일을 찾지 못했습니다.\n"
            "파일을 첨부한 메시지에 `save <경로>` 를 입력하거나, "
            "파일을 먼저 올린 후 `/save <경로>`를 입력해주세요."
        )
        return

    results = process_files_with_duplicate_check(files_found, dest_dir, dest_path, channel_id, user_id)
    respond("\n".join(results))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /create <폴더명> — 새 폴더 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command("/create")
def handle_create(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    if not _check_rate_limit(user_id, "create", CMD_COOLDOWN):
        respond(":hourglass: 잠시 후 다시 시도해주세요.")
        return

    folder_name = command["text"].strip()

    if not folder_name:
        respond(":warning: 폴더명을 입력해주세요. 예: `/create 20260327`")
        return

    if not validate_folder_name(folder_name):
        respond(
            ":x: 폴더명에 허용되지 않는 문자가 포함되어 있습니다.\n"
            "영문, 숫자, 한글, `_`, `-`, `.` 만 사용 가능합니다."
        )
        return

    new_path = resolve_path(channel_id, user_id, folder_name)

    try:
        target = safe_resolve(new_path)
    except ValueError:
        respond(":x: 접근할 수 없는 경로입니다.")
        return

    if target.exists():
        respond(f":warning: 이미 존재하는 폴더입니다: `/{new_path}`")
        return

    try:
        target.mkdir(parents=True, exist_ok=False)
        respond(f":white_check_mark: 폴더를 생성했습니다: `/{new_path}`")
        logger.info(f"폴더 생성: {target}")
    except FileExistsError:
        respond(f":warning: 이미 존재하는 폴더입니다: `/{new_path}`")
    except Exception:
        respond(":x: 폴더 생성 중 오류가 발생했습니다.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /fetch <경로> — 서버 파일/폴더를 Slack으로 전송
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.command("/fetch")
def handle_fetch(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    # C2 fix: /fetch 전용 rate limiting (더 긴 cooldown)
    if not _check_rate_limit(user_id, "fetch", FETCH_COOLDOWN):
        respond(f":hourglass: `/fetch` 는 {FETCH_COOLDOWN}초에 한 번만 사용 가능합니다.")
        return

    user_path = resolve_path(channel_id, user_id, command["text"])

    if not user_path or user_path == ".":
        respond(":warning: 경로를 입력해주세요. 예: `/fetch train.csv`")
        return

    try:
        target = safe_resolve(user_path)
    except ValueError:
        respond(":x: 접근할 수 없는 경로입니다.")
        return

    if not target.exists():
        respond(":x: 경로를 찾을 수 없습니다.")
        return

    # ── 단일 파일 ──
    if target.is_file():
        try:
            client.files_upload_v2(
                channel=channel_id,
                file=str(target),
                filename=target.name,
                initial_comment=f":inbox_tray: `{user_path}`",
            )
        except Exception:
            respond(":x: 파일 전송에 실패했습니다.")
        return

    # ── 폴더 → zip 압축 (symlink 제외) ──
    if target.is_dir():
        files_only = [
            f for f in target.rglob("*")
            if f.is_file() and not f.is_symlink()
        ]

        if not files_only:
            respond(f":open_file_folder: `{user_path}` — 빈 폴더입니다.")
            return

        # C2 fix: 파일 수 / 총 크기 제한
        if len(files_only) > MAX_ZIP_FILES:
            respond(
                f":x: 폴더 내 파일이 너무 많습니다 ({len(files_only)}개).\n"
                f"최대 {MAX_ZIP_FILES}개까지 지원합니다."
            )
            return

        try:
            total_size_mb = sum(f.stat().st_size for f in files_only) / (1024 * 1024)
        except OSError:
            total_size_mb = 0.0

        if total_size_mb > MAX_ZIP_SIZE_MB:
            respond(
                f":x: 폴더 크기가 너무 큽니다 ({total_size_mb:.1f}MB).\n"
                f"최대 {MAX_ZIP_SIZE_MB}MB까지 지원합니다."
            )
            return

        respond(
            f":hourglass_flowing_sand: `{user_path}` 폴더를 압축 중입니다... "
            f"({len(files_only)}개 파일, {total_size_mb:.1f}MB)"
        )

        tmp_zip = None
        try:
            tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            tmp_zip.close()

            with zipfile.ZipFile(tmp_zip.name, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in files_only:
                    zf.write(file, file.relative_to(target))

            client.files_upload_v2(
                channel=channel_id,
                file=tmp_zip.name,
                filename=f"{target.name}.zip",
                initial_comment=f":package: `{user_path}/` ({len(files_only)}개 파일, {total_size_mb:.1f}MB)",
            )
        except Exception:
            respond(":x: 폴더 전송에 실패했습니다.")
        finally:
            if tmp_zip:
                Path(tmp_zip.name).unlink(missing_ok=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  앱 시작
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    try:
        BOT_USER_ID = client.auth_test()["user_id"]
    except Exception as e:
        logger.error(f"Slack 인증 실패: {e}")
        raise SystemExit(1)

    BASE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    _load_state()

    # B3 fix: 예외 처리 추가된 백그라운드 cleanup 스레드
    cleanup_thread = threading.Thread(target=_auto_cleanup_loop, daemon=True)
    cleanup_thread.start()

    logger.info(f"File Gateway 시작 (bot_user_id={BOT_USER_ID})")
    logger.info(f"공유폴더: {BASE_STORAGE_PATH}")
    logger.info(f"상태 파일: {STATE_FILE}")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
