import logging
import os
import subprocess

from config.settings import DEVICE_UID, ALARM_SOUND_PATH, TTS_VOICE_PATH, SOUNDS_DIR, VOICES_DIR

logger = logging.getLogger(__name__)

_ALARM_STAMP = os.path.join(SOUNDS_DIR, ".alarm_updated_at")
_VOICE_STAMP = os.path.join(VOICES_DIR, ".voice_updated_at")


def _normalize_audio(file_path: str):
    """ffmpeg loudnorm으로 음량 정규화 (-14 LUFS). ffmpeg 없거나 실패하면 원본 유지."""
    tmp = file_path + ".norm.mp3"
    try:
        subprocess.run(
            ["ffmpeg", "-i", file_path,
             "-filter:a", "volume=20dB",
             "-ar", "44100", "-y", tmp],
            check=True, capture_output=True,
        )
        os.replace(tmp, file_path)
        logger.info("loudnorm 정규화 완료: %s", file_path)
    except Exception as e:
        logger.warning("loudnorm 실패, 원본 유지: %s", e)
        try:
            os.remove(tmp)
        except OSError:
            pass


def _read_stamp(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return ""


def _write_stamp(path: str, value: str):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(value)
    except Exception as e:
        logger.warning("stamp write failed (%s): %s", path, e)


def sync_alarm_sound() -> bool:
    """보호자가 업로드한 알림음 → assets/sounds/alarm.mp3"""
    if not DEVICE_UID:
        return False
    try:
        from api.client import fetch_sound_meta, download_sound
        meta = fetch_sound_meta()
    except Exception as e:
        logger.warning("sync_alarm_sound fetch failed: %s", e)
        return False

    if not meta or not meta.get("url"):
        return False

    stamp = str(meta.get("updated_at", ""))
    if stamp and stamp == _read_stamp(_ALARM_STAMP):
        return False

    if download_sound(meta["url"], ALARM_SOUND_PATH):
        _write_stamp(_ALARM_STAMP, stamp)
        logger.info("alarm sound updated: %s", ALARM_SOUND_PATH)
        return True
    return False


def sync_tts_voice() -> bool:
    """보호자 TTS 음성 → assets/voices/voice.mp3"""
    if not DEVICE_UID:
        return False
    try:
        from api.client import fetch_voice_meta, download_sound
        meta = fetch_voice_meta()
    except Exception as e:
        logger.warning("sync_tts_voice fetch failed: %s", e)
        return False

    if not meta or not meta.get("url"):
        return False

    stamp = str(meta.get("file_path") or meta.get("updated_at") or "")
    if stamp and stamp == _read_stamp(_VOICE_STAMP):
        return False

    if download_sound(meta["url"], TTS_VOICE_PATH):
        _normalize_audio(TTS_VOICE_PATH)
        _write_stamp(_VOICE_STAMP, stamp)
        logger.info("tts voice updated: %s", TTS_VOICE_PATH)
        return True
    return False


def sync_sound() -> bool:
    """알림음 + TTS 음성 동시 동기화. 하나라도 갱신되면 True."""
    a = sync_alarm_sound()
    b = sync_tts_voice()
    return a or b
