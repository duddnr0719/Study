"""
File Gateway - Slack ↔ 서버 공유폴더 파일 브릿지

사용법:
  파일 + "save <폴더경로>" : 파일을 첨부하고 메시지에 save를 입력하면 서버에 저장
  /save <폴더경로>         : 채널의 최근 파일을 서버에 저장 (파일 첨부 불가 시)
  /fetch <경로>            : 서버 파일/폴더를 Slack으로 전송 (폴더는 zip 압축)
  /ls <경로>               : 서버 폴더의 파일 목록 조회
"""

import os
import re
import io
import zipfile
import tempfile
import logging
import urllib.request
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


# ── 보안: Path Traversal 방지 ──
def safe_resolve(user_path: str) -> Path:
    """사용자 입력 경로를 BASE_STORAGE_PATH 내부로 제한"""
    target = (BASE_STORAGE_PATH / user_path).resolve()
    if not str(target).startswith(str(BASE_STORAGE_PATH)):
        raise ValueError(f"접근 불가: 공유폴더 범위를 벗어난 경로입니다.")
    return target


def format_size(size_bytes: int) -> str:
    """바이트를 사람이 읽기 쉬운 단위로 변환"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def download_and_save_files(files, dest_dir: Path, dest_path: str) -> list[str]:
    """Slack 파일 목록을 다운로드하여 dest_dir에 저장. 결과 메시지 리스트 반환."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for file_info in files:
        filename = file_info["name"]
        download_url = file_info["url_private"]
        try:
            req = urllib.request.Request(
                download_url,
                headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            )
            with urllib.request.urlopen(req) as resp:
                file_data = resp.read()

            save_path = dest_dir / filename
            save_path.write_bytes(file_data)
            results.append(f":white_check_mark: `{filename}` → `{dest_path}/{filename}`")
            logger.info(f"저장 완료: {save_path}")
        except Exception as e:
            results.append(f":x: `{filename}` 저장 실패: {e}")
            logger.error(f"파일 저장 실패 ({filename}): {e}")
    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  메시지 이벤트: 파일 + "save <경로>" → 서버 저장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.event("message")
def handle_message_save(event, say):
    # 봇 자신의 메시지 무시
    if event.get("user") == BOT_USER_ID or event.get("bot_id"):
        return

    text = event.get("text", "").strip()
    files = event.get("files", [])

    # "save" 또는 "save <경로>" 패턴 매칭
    match = re.match(r"^save(?:\s+(.+))?$", text, re.IGNORECASE)
    if not match or not files:
        return

    dest_path = (match.group(1) or ".").strip()

    try:
        dest_dir = safe_resolve(dest_path)
    except ValueError as e:
        say(f":x: {e}")
        return

    valid_files = [f for f in files if f.get("mode") != "tombstone"]
    if not valid_files:
        say(":warning: 저장할 수 있는 파일이 없습니다.")
        return

    results = download_and_save_files(valid_files, dest_dir, dest_path)
    say("\n".join(results))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /ls <경로> — 폴더 목록 조회
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/ls")
def handle_ls(ack, command, respond):
    ack()
    user_path = command["text"].strip() or "."

    try:
        target = safe_resolve(user_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    if not target.exists():
        respond(f":x: 경로를 찾을 수 없습니다: `{user_path}`")
        return

    if not target.is_dir():
        # 단일 파일 정보
        size = format_size(target.stat().st_size)
        respond(f":page_facing_up: `{target.name}` ({size})")
        return

    # 폴더 내용 나열
    items = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    if not items:
        respond(f":open_file_folder: `{user_path}` — 빈 폴더입니다.")
        return

    lines = [f":open_file_folder: *`{user_path}`* 목록:\n"]
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
    dest_path = command["text"].strip() or "."

    try:
        dest_dir = safe_resolve(dest_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    # 슬래시 커맨드와 함께 첨부된 파일이 없는 경우 안내
    # Slack은 슬래시 커맨드에 파일 첨부를 직접 지원하지 않음
    # → 메시지에 파일을 올리고 스레드에서 /save 를 사용하는 방식
    # → 또는 채널의 최근 파일을 자동으로 찾는 방식

    # 채널의 최근 파일 가져오기
    channel_id = command["channel_id"]
    try:
        result = client.conversations_history(channel=channel_id, limit=10)
    except Exception as e:
        respond(f":x: 채널 히스토리 조회 실패: {e}")
        return

    # 최근 메시지에서 파일 찾기 (봇이 올린 파일은 제외)
    files_found = []
    for msg in result.get("messages", []):
        msg_user = msg.get("user", "N/A")
        msg_bot_id = msg.get("bot_id", "N/A")
        msg_subtype = msg.get("subtype", "N/A")
        has_files = "files" in msg
        logger.info(f"[/save 디버그] user={msg_user} bot_id={msg_bot_id} subtype={msg_subtype} has_files={has_files}")

        # 봇 자신이 올린 메시지는 건너뛰기
        if msg.get("user") == BOT_USER_ID or msg.get("bot_id"):
            logger.info(f"[/save 디버그] → 봇 메시지, 건너뜀")
            continue
        if "files" in msg:
            for f in msg["files"]:
                logger.info(f"[/save 디버그] → 파일 발견: {f['name']} mode={f.get('mode')}")
                if f.get("mode") != "tombstone":  # 삭제된 파일 제외
                    files_found.append(f)
            if files_found:
                break  # 가장 최근 사용자 파일이 있는 메시지에서 멈춤

    if not files_found:
        respond(
            ":warning: 저장할 파일을 찾지 못했습니다.\n"
            "채널에 파일을 먼저 업로드한 후 `/save <폴더경로>`를 입력해주세요."
        )
        return

    results = download_and_save_files(files_found, dest_dir, dest_path)
    respond("\n".join(results))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /fetch <경로> — 서버 파일/폴더를 Slack으로 전송
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.command("/fetch")
def handle_fetch(ack, command, respond):
    ack()
    user_path = command["text"].strip()

    if not user_path:
        respond(":warning: 경로를 입력해주세요. 예: `/fetch datasets/train.csv`")
        return

    try:
        target = safe_resolve(user_path)
    except ValueError as e:
        respond(f":x: {e}")
        return

    if not target.exists():
        respond(f":x: 경로를 찾을 수 없습니다: `{user_path}`")
        return

    channel_id = command["channel_id"]

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
        files_in_dir = list(target.rglob("*"))
        files_only = [f for f in files_in_dir if f.is_file()]

        if not files_only:
            respond(f":open_file_folder: `{user_path}` — 빈 폴더입니다.")
            return

        respond(f":hourglass_flowing_sand: `{user_path}` 폴더를 압축 중입니다... ({len(files_only)}개 파일)")

        try:
            # 메모리에서 zip 생성
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in files_only:
                    arcname = file.relative_to(target)
                    zf.write(file, arcname)

            zip_buffer.seek(0)
            zip_filename = f"{target.name}.zip"
            client.files_upload_v2(
                channel=channel_id,
                file=zip_buffer.read(),
                filename=zip_filename,
                initial_comment=f":package: `{user_path}/` ({len(files_only)}개 파일)",
            )
        except Exception as e:
            respond(f":x: 폴더 전송 실패: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  앱 시작
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    # 봇 자신의 user_id 조회
    BOT_USER_ID = client.auth_test()["user_id"]

    # BASE_STORAGE_PATH 폴더 자동 생성
    BASE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
    logger.info(f"File Gateway 시작 (bot_user_id={BOT_USER_ID})")
    logger.info(f"공유폴더: {BASE_STORAGE_PATH}")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
