import logging
import os
import re
import subprocess

from config.settings import SOUNDS_DIR, VOICES_DIR, ALARM_SOUND_PATH, TTS_VOICE_PATH, AUDIO_DEVICE

logger = logging.getLogger("Alarm")

_pygame_ready = False
_fallback_process = None   # mpg123 fallback용


# ── USB 오디오 카드 탐지 ──────────────────────────────────────────────────────

def _detect_usb_card() -> int | None:
    """aplay -l 출력에서 USB Audio 카드 번호를 반환. 없으면 None."""
    try:
        out = subprocess.check_output(
            ["aplay", "-l"], stderr=subprocess.DEVNULL, text=True, timeout=3
        )
        for line in out.splitlines():
            if re.search(r"(?i)\busb\b", line):
                m = re.search(r"card\s+(\d+)", line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


# ── pygame 초기화 ────────────────────────────────────────────────────────────

def _init_pygame() -> bool:
    global _pygame_ready
    if _pygame_ready:
        return True
    try:
        import pygame

        # .env CAREFULL_AUDIO_DEVICE 우선, 없으면 USB 카드 자동 탐지
        if AUDIO_DEVICE:
            os.environ.setdefault("SDL_AUDIODRIVER", "alsa")
            os.environ.setdefault("AUDIODEV", AUDIO_DEVICE)
            logger.info(".env 설정 오디오 장치 사용: %s", AUDIO_DEVICE)
        else:
            usb = _detect_usb_card()
            if usb is not None:
                os.environ.setdefault("SDL_AUDIODRIVER", "alsa")
                os.environ.setdefault("AUDIODEV", f"hw:{usb},0")
                logger.info("USB 오디오 카드 %d 감지 → AUDIODEV=hw:%d,0", usb, usb)
            else:
                logger.info("USB 오디오 카드 미감지, 시스템 기본 오디오 사용")

        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        _pygame_ready = True
        return True
    except Exception as e:
        logger.error("pygame mixer 초기화 실패: %s", e)
        return False


# ── 공개 API ─────────────────────────────────────────────────────────────────

def play_alarm(filename: str = None, loop: bool = False):
    """알람 재생.

    파일 탐색 순서:
      1. filename 지정 시 assets/sounds/, assets/voices/ 에서 탐색
      2. assets/sounds/alarm.mp3   (보호자 업로드 알림음)
      3. assets/voices/voice.mp3   (보호자 TTS 음성)
      4. assets/sounds/default_alarm.mp3  (기본 알림음)

    loop=True 이면 stop_alarm() 호출 전까지 반복.
    """
    stop_alarm()

    candidates = []
    if filename:
        candidates += [os.path.join(SOUNDS_DIR, filename), os.path.join(VOICES_DIR, filename)]
    candidates += [
        ALARM_SOUND_PATH,
        TTS_VOICE_PATH,
        os.path.join(SOUNDS_DIR, "default_alarm.mp3"),
    ]

    file_path = next((p for p in candidates if os.path.exists(p)), None)
    if not file_path:
        logger.error("알람 파일 없음: %s", candidates)
        return

    logger.info("알람 재생: %s  loop=%s", file_path, loop)

    # ── pygame (우선) ────────────────────────────────────────────────────────
    if _init_pygame():
        try:
            import pygame
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play(loops=-1 if loop else 0)
            logger.info("pygame 재생 시작")
            return
        except Exception as e:
            logger.warning("pygame 재생 실패, mpg123 fallback: %s", e)

    # ── mpg123 fallback ──────────────────────────────────────────────────────
    global _fallback_process
    try:
        cmd = ["mpg123", "-q"]
        if AUDIO_DEVICE:
            cmd += ["-o", "alsa", "-a", AUDIO_DEVICE]
        else:
            usb = _detect_usb_card()
            if usb is not None:
                cmd += ["-o", "alsa", "-a", f"plughw:{usb},0"]
        if loop:
            cmd += ["--loop", "-1"]
        cmd.append(file_path)
        _fallback_process = subprocess.Popen(cmd)
        logger.info("mpg123 fallback 재생 시작")
    except FileNotFoundError:
        logger.error("mpg123 미설치. 설치: sudo apt install mpg123")
    except Exception as e:
        logger.error("mpg123 실패: %s", e)


def stop_alarm():
    """재생 중인 알람을 즉시 정지."""
    global _fallback_process

    # pygame 정지
    try:
        import pygame
        if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            logger.info("pygame 알람 정지")
    except Exception:
        pass

    # mpg123 fallback 정지
    if _fallback_process is not None:
        try:
            if _fallback_process.poll() is None:
                _fallback_process.terminate()
                _fallback_process.wait(timeout=1)
        except Exception:
            try:
                _fallback_process.kill()
                _fallback_process.wait(timeout=1)
            except Exception:
                pass
        finally:
            _fallback_process = None


def is_playing() -> bool:
    """현재 알람이 재생 중인지 확인."""
    try:
        import pygame
        if pygame.mixer.get_init():
            return pygame.mixer.music.get_busy()
    except Exception:
        pass
    if _fallback_process is not None:
        return _fallback_process.poll() is None
    return False
