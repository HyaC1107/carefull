import os
import subprocess
import logging
from config.settings import VOICES_DIR

logger = logging.getLogger("Alarm")

_alarm_process = None

def play_alarm(filename=None):
    """
    알람 소리 재생
    우선순위:
    1. filename이 명시된 경우 (예: voice_1.mp3)
    2. 서버와 동기화된 커스텀 알림음 (alarm1.mp3)
    3. 로컬 기본 알림음 (default_alarm.mp3)
    """
    global _alarm_process
    stop_alarm()
    
    # 1. 파일 후보 리스트 (순서대로 확인)
    candidates = []
    if filename:
        candidates.append(filename)
    candidates.append("alarm1.mp3")
    candidates.append("default_alarm.mp3")
    
    file_path = None
    for cand in candidates:
        path = os.path.join(VOICES_DIR, cand)
        if os.path.exists(path):
            file_path = path
            break
            
    if not file_path:
        logger.error("No alarm files found (alarm1.mp3, default_alarm.mp3 both missing)")
        return

    # 3. 재생
    logger.info(f"Playing alarm: {file_path}")
    try:
        # mpg123을 사용하여 비동기 재생
        _alarm_process = subprocess.Popen(["mpg123", "-q", file_path])
    except Exception as e:
        logger.error(f"Failed to play alarm: {e}")

def stop_alarm():
    """알람 소리 정지"""
    global _alarm_process
    if _alarm_process:
        logger.info("Stopping alarm sound...")
        try:
            if _alarm_process.poll() is None:
                _alarm_process.terminate()
                _alarm_process.wait(timeout=1)
        except Exception:
            try:
                if _alarm_process:
                    _alarm_process.kill()
                    _alarm_process.wait(timeout=1)
            except Exception as e:
                logger.warning("alarm process kill failed: %s", e)
        finally:
            _alarm_process = None
