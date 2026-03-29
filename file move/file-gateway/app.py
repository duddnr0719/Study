"""
File Gateway - Slack ↔ 서버 공유폴더 파일 브릿지

사용법:
  파일 + "save <폴더경로>" : 파일을 첨부하고 메시지에 save를 입력하면 서버에 저장
  /save <폴더경로>         : 채널의 최근 파일을 서버에 저장 (파일 첨부 불가 시)
  /fetch <경로>            : 서버 파일/폴더를 Slack으로 전송 (폴더는 zip 압축)
  /ls <경로>               : 서버 폴더의 파일 목록 조회
  /cd <경로>               : 현재 디렉토리 이동 (.. 으로 상위 이동 가능)
  /pwd                     : 현재 디렉토리 확인
"""

import os
import re
import io
import time
import uuid
import zipfile
import logging
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

app = App(token=SLACK_BOT_TOKEN)
client = WebClient(token=SLACK_BOT_TOKEN)

# 봇 자신의 user_id (시작 시 조회)
BOT_USER_ID = None

# 채널별 현재 디렉토리 상태 (channel_id → 상대경로 문자열)
channel_dirs: dict[str, str] = {}

# 중복 파일 처리 대기 중인 작업 (pending_id → 작업 정보)
pending_saves: dict[str, dict] = {}

# pending_saves TTL (초)
PENDING_SAVE_TTL = 600


def cleanup_expired_pending():
    """만료된 pending_saves 항목 제거 (TTL: 10분)"""
    now = time.time()
    expired = [k for k, v in list(pending_saves.items()) if now - v["created_at"] > PENDING_SAVE_TTL]
    for k in expired:
        pending_saves.pop(k, None)
    if expired:
        logger.info(f"만료된 pending_saves {len(expired)}건 정리")


# ── 채널별 현재 디렉토리 관리 ──
def get_current_dir(channel_id: str) -> str:
    return channel_dirs.get(channel_id, ".")


def set_current_dir(channel_id: str, path: str):
    channel_dirs[channel_id] = path


def resolve_path(channel_id: str, user_input: str) -> str:
    user_input = user_input.strip()
    if not user_input:
        return get_current_dir(channel_id)
    if user_input.startswith("/"):
        return user_input.lstrip("/") or "."
    current = get_current_dir(channel_id)
    if current == ".":
        return user_input
    return f"{current}/{user_input}"


# ── 보안: Path Traversal 방지 ──
def safe_resolve(user_path: str) -> Path:
    target = (BASE_STORAGE_PATH / user_path).resolve()
    if not str(target).startswith(str(BASE_STORAGE_PATH)):
        raise ValueError("접근 불가: 공유폴더 범위를 벗어난 경로입니다.")
    return target


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def make_renamed_path(dest_dir: Path, filename: str) -> Path:
    """중복 시 타임스탬프를 붙인 새 경로 생성. 예: report.xlsx → report_20260327_143022.xlsx"""
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return dest_dir / f"{stem}_{timestamp}{suffix}"


def download_file(file_info: dict) -> bytes:
    """Slack 파일을 다운로드해 bytes로 반환"""
    req = urllib.request.Request(
        file_info["url_private"],
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
    )
    with urllib.request.urlopen(req) as resp:
        return resp.read()


def send_duplicate_prompt(channel_id: str, filename: str, dest_path: str, pending_id: str):
    """중복 파일 감지 시 사용자에게 선택 버튼 전송"""
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


def process_files_with_duplicate_check(files: list, dest_dir: Path, dest_path: str, channel_id: str) -> list[str]:
    """
    파일 목록을 순회하며 저장.
    - 중복 없으면 바로 저장
    - 중복 있으면 pending_saves에 등록 후 버튼 메시지 전송
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for file_info in files:
        filename = file_info["name"]
        save_path = dest_dir / filename

        if save_path.exists():
            # 중복 → pending에 등록하고 버튼 전송
            cleanup_expired_pending()
            pending_id = str(uuid.uuid4())
            pending_saves[pending_id] = {
                "file_info": file_info,
                "dest_dir": dest_dir,
                "dest_path": dest_path,
                "filename": filename,
                "channel_id": channel_id,
                "created_at": time.time(),
            }
            send_duplicate_prompt(channel_id, filename, dest_path, pending_id)
            results.append(f":hourglass_flowing_sand: `{filename}` — 중복 파일, 처리 방식을 선택해주세요.")
        else:
            # 중복 없음 → 바로 저장
            try:
                file_data = download_file(file_info)
                save_path.write_bytes(file_data)
                results.append(f":white_check_mark: `{filename}` → `{dest_path}/{filename}`")
                logger.info(f"저장 완료: {save_path}")
            except Exception as e:
                results.append(f":x: `{filename}` 저장 실패: {e}")
                logger.error(f"파일 저장 실패 ({filename}): {e}")

    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션: 덮어쓰기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.action("fg_overwrite")
def action_overwrite(ack, body, client):
    ack()
    cleanup_expired_pending()
    pending_id = body["actions"][0]["value"]
    pending = pending_saves.pop(pending_id, None)
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    if not pending:
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=":x: 처리 시간이 초과되었거나 이미 처리된 작업입니다."
        )
        return

    filename = pending["filename"]
    dest_dir = pending["dest_dir"]
    dest_path = pending["dest_path"]

    try:
        file_data = download_file(pending["file_info"])
        save_path = dest_dir / filename
        save_path.write_bytes(file_data)
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":white_check_mark: `{filename}` → `{dest_path}/{filename}` (덮어쓰기 완료)",
            blocks=[],
        )
        logger.info(f"덮어쓰기 완료: {save_path}")
    except Exception as e:
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":x: `{filename}` 덮어쓰기 실패: {e}",
            blocks=[],
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션: 새 이름으로 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.action("fg_rename")
def action_rename(ack, body, client):
    ack()
    cleanup_expired_pending()
    pending_id = body["actions"][0]["value"]
    pending = pending_saves.pop(pending_id, None)
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    if not pending:
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=":x: 처리 시간이 초과되었거나 이미 처리된 작업입니다."
        )
        return

    filename = pending["filename"]
    dest_dir = pending["dest_dir"]
    dest_path = pending["dest_path"]

    try:
        file_data = download_file(pending["file_info"])
        new_path = make_renamed_path(dest_dir, filename)
        new_path.write_bytes(file_data)
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":white_check_mark: `{filename}` → `{dest_path}/{new_path.name}` (새 이름으로 저장)",
            blocks=[],
        )
        logger.info(f"새 이름 저장 완료: {new_path}")
    except Exception as e:
        client.chat_update(
            channel=channel_id, ts=message_ts,
            text=f":x: `{filename}` 저장 실패: {e}",
            blocks=[],
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  버튼 액션: 취소
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.action("fg_cancel")
def action_cancel(ack, body, client):
    ack()
    cleanup_expired_pending()
    pending_id = body["actions"][0]["value"]
    pending_saves.pop(pending_id, None)
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]
    filename = body["message"]["blocks"][0]["text"]["text"].split("`")[1].split("/")[-1]

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

    match = re.match(r"^save(?:\s+(.+))?$", text, re.IGNORECASE)
    if not match or not files:
        return

    user_input = (match.group(1) or "").strip()
    dest_path = resolve_path(channel_id, user_input)

    try:
        dest_dir = safe_resolve(dest_path)
    except ValueError as e:
        say(f":x: {e}")
        return

    valid_files = [f for f in files if f.get("mode") != "tombstone"]
    if not valid_files:
        say(":warning: 저장할 수 있는 파일이 없습니다.")
        return

    results = process_files_with_duplicate_check(valid_files, dest_dir, dest_path, channel_id)
    say("\n".join(results))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /cd <경로> — 디렉토리 이동
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/cd")
def handle_cd(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_input = command["text"].strip()

    if not user_input:
        set_current_dir(channel_id, ".")
        respond(":open_file_folder: 루트 디렉토리로 이동했습니다: `/`")
        return

    new_path = resolve_path(channel_id, user_input)

    try:
        resolved = (BASE_STORAGE_PATH / new_path).resolve()
        if not str(resolved).startswith(str(BASE_STORAGE_PATH)):
            respond(":x: 공유폴더 범위를 벗어날 수 없습니다.")
            return
        if not resolved.exists():
            respond(f":x: 경로를 찾을 수 없습니다: `{new_path}`")
            return
        if not resolved.is_dir():
            respond(f":x: 디렉토리가 아닙니다: `{new_path}`")
            return
    except Exception as e:
        respond(f":x: {e}")
        return

    relative = str(resolved.relative_to(BASE_STORAGE_PATH))
    display = "/" if relative == "." else f"/{relative}"
    set_current_dir(channel_id, relative)
    respond(f":open_file_folder: `{display}` 로 이동했습니다.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /pwd — 현재 디렉토리 확인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/pwd")
def handle_pwd(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    current = get_current_dir(channel_id)
    display = "/" if current == "." else f"/{current}"
    respond(f":round_pushpin: 현재 디렉토리: `{display}`")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /ls <경로> — 폴더 목록 조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/ls")
def handle_ls(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_path = resolve_path(channel_id, command["text"])

    try:
        target = safe_resolve(user_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    if not target.exists():
        respond(f":x: 경로를 찾을 수 없습니다: `{user_path}`")
        return

    if not target.is_dir():
        size = format_size(target.stat().st_size)
        respond(f":page_facing_up: `{target.name}` ({size})")
        return

    items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    display_path = "/" if user_path == "." else f"/{user_path}"

    if not items:
        respond(f":open_file_folder: `{display_path}` — 빈 폴더입니다.")
        return

    lines = [f":open_file_folder: *`{display_path}`* 목록:\n"]
    for item in items:
        if item.is_dir():
            lines.append(f"  :file_folder: `{item.name}/`")
        else:
            size = format_size(item.stat().st_size)
            lines.append(f"  :page_facing_up: `{item.name}` ({size})")

    respond("\n".join(lines))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /save <폴더경로> — Slack 파일을 서버에 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/save")
def handle_save(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    dest_path = resolve_path(channel_id, command["text"])

    try:
        dest_dir = safe_resolve(dest_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    try:
        result = client.conversations_history(channel=channel_id, limit=10)
    except Exception as e:
        respond(f":x: 채널 히스토리 조회 실패: {e}")
        return

    files_found = []
    for msg in result.get("messages", []):
        if msg.get("user") == BOT_USER_ID or msg.get("bot_id"):
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
            "채널에 파일을 먼저 업로드한 후 `/save <폴더경로>`를 입력해주세요."
        )
        return

    results = process_files_with_duplicate_check(files_found, dest_dir, dest_path, channel_id)
    respond("\n".join(results))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /create <폴더명> — 새 폴더 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/create")
def handle_create(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    folder_name = command["text"].strip()

    if not folder_name:
        respond(":warning: 폴더명을 입력해주세요. 예: `/create 20260327`")
        return

    new_path = resolve_path(channel_id, folder_name)

    try:
        target = safe_resolve(new_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    if target.exists():
        respond(f":warning: 이미 존재하는 폴더입니다: `/{new_path}`")
        return

    try:
        target.mkdir(parents=True, exist_ok=False)
        display = f"/{new_path}"
        respond(f":white_check_mark: 폴더를 생성했습니다: `{display}`")
        logger.info(f"폴더 생성: {target}")
    except Exception as e:
        respond(f":x: 폴더 생성 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /fetch <경로> — 서버 파일/폴더를 Slack으로 전송
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/fetch")
def handle_fetch(ack, command, respond):
    ack()
    channel_id = command["channel_id"]
    user_path = resolve_path(channel_id, command["text"])

    if not user_path or user_path == ".":
        respond(":warning: 경로를 입력해주세요. 예: `/fetch train.csv`")
        return

    try:
        target = safe_resolve(user_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    if not target.exists():
        respond(f":x: 경로를 찾을 수 없습니다: `{user_path}`")
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
        except Exception as e:
            respond(f":x: 파일 전송 실패: {e}")
        return

    # ── 폴더 → zip 압축 후 전송 ──
    if target.is_dir():
        files_only = [f for f in target.rglob("*") if f.is_file()]

        if not files_only:
            respond(f":open_file_folder: `{user_path}` — 빈 폴더입니다.")
            return

        respond(f":hourglass_flowing_sand: `{user_path}` 폴더를 압축 중입니다... ({len(files_only)}개 파일)")

        try:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in files_only:
                    zf.write(file, file.relative_to(target))

            zip_buffer.seek(0)
            client.files_upload_v2(
                channel=channel_id,
                file=zip_buffer.read(),
                filename=f"{target.name}.zip",
                initial_comment=f":package: `{user_path}/` ({len(files_only)}개 파일)",
            )
        except Exception as e:
            respond(f":x: 폴더 전송 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  앱 시작
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    BOT_USER_ID = client.auth_test()["user_id"]
    BASE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"File Gateway 시작 (bot_user_id={BOT_USER_ID})")
    logger.info(f"공유폴더: {BASE_STORAGE_PATH}")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
