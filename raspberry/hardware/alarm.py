import os
import subprocess
import logging

logger = logging.getLogger("Alarm")

# 알람 소리 파일 경로 (없을 경우 시스템 비프음이나 생략 가능)
ALARM_FILE = os.path.join(os.path.dirname(__file__), "..", "assets", "sounds", "alarm.mp3")

_alarm_process = None

def play_alarm():
    """알람 소리 재생 (비동기)"""
    global _alarm_process
    if _alarm_process and _alarm_process.poll() is None:
        return # 이미 재생 중
    
    logger.info("Playing alarm sound...")
    try:
        if os.path.exists(ALARM_FILE):
            # mpg123 또는 ogg123 등을 사용하여 백그라운드 재생
            _alarm_process = subprocess.Popen(["mpg123", "-q", ALARM_FILE])
        else:
            logger.warning(f"Alarm file not found: {ALARM_FILE}. Using system beep.")
            # 알람 파일이 없으면 비프음 등으로 대체 가능
    except Exception as e:
        logger.error(f"Failed to play alarm: {e}")

def stop_alarm():
    """알람 소리 정지"""
    global _alarm_process
    if _alarm_process:
        logger.info("Stopping alarm sound...")
        _alarm_process.terminate()
        _alarm_process = None
