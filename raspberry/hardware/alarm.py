import os
import subprocess
import logging
from config.settings import VOICES_DIR

logger = logging.getLogger("Alarm")

_alarm_process = None

def play_alarm(filename=None):
    """
    알람 소리 재생
    1. filename이 없으면 (결제 안 한 사용자): default_voice.mp3 재생
    2. filename이 있으면 (결제한 사용자): 해당 파일 재생 (ElevenLabs 생성 파일)
    """
    global _alarm_process
    stop_alarm()
    
    # 1. 파일 이름 결정
    target_file = filename if filename else "default_voice.mp3"
    file_path = os.path.join(VOICES_DIR, target_file)
    
    # 2. 파일 존재 여부 확인
    if not os.path.exists(file_path):
        logger.error(f"Alarm file not found: {file_path}")
        # 만약 요청한 파일이 없는데 그게 custom 파일이었다면 default로라도 시도
        if target_file != "default_voice.mp3":
            logger.info("Attempting to play default_voice.mp3 as fallback.")
            file_path = os.path.join(VOICES_DIR, "default_voice.mp3")
            if not os.path.exists(file_path):
                logger.error("Default alarm file also missing.")
                return
        else:
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
