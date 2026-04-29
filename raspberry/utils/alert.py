import logging
import os

logger = logging.getLogger(__name__)


def alert_user():
    print("[알림] 복약 시간입니다!")
    _play_alarm()


def _play_alarm():
    from config.settings import TTS_FILE_PATH
    if not os.path.exists(TTS_FILE_PATH):
        logger.warning("alarm file not found: %s", TTS_FILE_PATH)
        return
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(TTS_FILE_PATH)
        pygame.mixer.music.play()
    except Exception as e:
        logger.warning("alarm playback failed: %s", e)
