import logging
import os
import subprocess

from config.settings import SOUNDS_DIR, VOICES_DIR

logger = logging.getLogger("Alarm")

_alarm_process = None


def play_alarm(filename: str = None, loop: bool = False):
    """알람 재생.

    파일 탐색 순서:
      1. assets/sounds/default_alarm.mp3  (기본 내장음)
      2. voices/default_alarm.mp3         (이전 경로 fallback)
      filename 지정 시 위 두 디렉토리에서 먼저 탐색.

    loop=True 이면 stop_alarm() 호출 전까지 반복 재생.
    """
    global _alarm_process
    stop_alarm()

    candidates = []
    if filename:
        candidates.append(os.path.join(SOUNDS_DIR, filename))
        candidates.append(os.path.join(VOICES_DIR, filename))
    candidates.append(os.path.join(SOUNDS_DIR, "default_alarm.mp3"))
    candidates.append(os.path.join(VOICES_DIR, "default_alarm.mp3"))

    file_path = next((p for p in candidates if os.path.exists(p)), None)
    if not file_path:
        logger.error("알람 파일을 찾을 수 없습니다: %s", candidates)
        return

    logger.info("알람 재생: %s (loop=%s)", file_path, loop)
    try:
        cmd = ["mpg123", "-q"]
        if loop:
            cmd += ["--loop", "-1"]
        cmd.append(file_path)
        _alarm_process = subprocess.Popen(cmd)
    except FileNotFoundError:
        logger.error("mpg123 미설치 — sudo apt install mpg123")
    except Exception as e:
        logger.error("알람 재생 실패: %s", e)


def stop_alarm():
    """재생 중인 알람을 즉시 정지."""
    global _alarm_process
    if _alarm_process is None:
        return
    logger.info("알람 정지")
    try:
        if _alarm_process.poll() is None:
            _alarm_process.terminate()
            _alarm_process.wait(timeout=1)
    except Exception:
        try:
            _alarm_process.kill()
            _alarm_process.wait(timeout=1)
        except Exception as e:
            logger.warning("알람 프로세스 강제종료 실패: %s", e)
    finally:
        _alarm_process = None


def is_playing() -> bool:
    """현재 알람이 재생 중인지 확인."""
    return _alarm_process is not None and _alarm_process.poll() is None
