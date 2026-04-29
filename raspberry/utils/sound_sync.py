import logging
import os

from config.settings import DEVICE_UID, TTS_FILE_PATH, VOICES_DIR

logger = logging.getLogger(__name__)

# 마지막 다운로드 타임스탬프를 파일로 캐싱
_STAMP_FILE = os.path.join(VOICES_DIR, ".sound_updated_at")


def _read_stamp() -> str:
    try:
        with open(_STAMP_FILE) as f:
            return f.read().strip()
    except Exception:
        return ""


def _write_stamp(value: str):
    try:
        os.makedirs(VOICES_DIR, exist_ok=True)
        with open(_STAMP_FILE, "w") as f:
            f.write(value)
    except Exception as e:
        logger.warning("sound stamp write failed: %s", e)


def sync_sound() -> bool:
    """서버 알림음이 바뀐 경우에만 다운로드. 새 파일 적용 시 True 반환."""
    if not DEVICE_UID:
        return False

    try:
        from api.client import download_sound, fetch_sound_meta
        meta = fetch_sound_meta()
    except Exception as e:
        logger.warning("sync_sound fetch failed: %s", e)
        return False

    if not meta or not meta.get("url"):
        return False

    server_stamp = str(meta.get("updated_at", ""))
    if server_stamp and server_stamp == _read_stamp():
        return False  # 변경 없음 → 스킵

    success = download_sound(meta["url"], TTS_FILE_PATH)
    if success:
        _write_stamp(server_stamp)
        logger.info("alarm sound updated: %s", TTS_FILE_PATH)
    return success
