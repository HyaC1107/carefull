import time
import logging

from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE

logger = logging.getLogger(__name__)

MODE_AUTH = "auth"
MODE_REGISTER = "register"

AUTH_TIMEOUT_SEC = 7           # 얼굴 인증 최대 시도 시간 (초과 시 지문 폴백)
_REGISTER_TARGET = 20
_REGISTER_COOLDOWN_SEC = 0.6   # 캡처 간격
_DETECT_EVERY_N = 8            # N프레임마다 1번 AI 검출
_FACE_MARGIN = 0.2

# 등록 방향 안내 (4장씩 × 5방향 = 20장)
_PHASES = ["정면", "위", "아래", "왼쪽", "오른쪽"]
_PHOTOS_PER_PHASE = 4
_PHASE_PAUSE_SEC = 2.0   # 방향 전환 전 카운트다운 대기 시간


class FaceThread(QThread):
    frame_ready = pyqtSignal(object)       # BGR ndarray
    auth_success = pyqtSignal(str, float)  # matched user name, similarity score
    auth_failed = pyqtSignal()
    capture_progress = pyqtSignal(int)     # captured count (register mode)
    capture_done = pyqtSignal(list)        # list of face BGR images (register mode)
    phase_changed = pyqtSignal(int, str)   # (phase_idx, direction_label) 방향 전환 안내

    def __init__(self, mode: str = MODE_AUTH, max_retries: int = 5, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._max_retries = max_retries
        self._running = False

    def run(self):
        self._running = True
        logger.info(f"[FACE_THREAD] Started (mode: {self._mode})")
        
        if UI_TEST_MODE:
            self._run_test_mode()
            return
            
        if self._mode == MODE_AUTH:
            self._run_auth()
        else:
            self._run_register()

    def _run_test_mode(self):
        """UI 테스트 모드: 카메라/AI 없이 2초 후 성공 시뮬레이션."""
        if self._mode == MODE_AUTH:
            self.msleep(2000)
            if self._running:
                logger.info("[FACE_THREAD] Test mode auth success")
                self.auth_success.emit("테스트유저", 0.99)
        else:
            for i in range(1, _REGISTER_TARGET + 1):
                if not self._running:
                    return
                self.capture_progress.emit(i)
                self.msleep(100)
            if self._running:
                logger.info("[FACE_THREAD] Test mode register complete")
                self.capture_done.emit([])

    def stop(self):
        self._running = False
        logger.info("[FACE_THREAD] Stopping...")

    def _run_auth(self):
        """
        [최적화] 2초 동안 15장의 RGB 프레임을 수집.
        속도와 정확도의 균형을 맞춘 설정.
        """
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        import cv2

        deadline = None
        face_imgs = []
        max_capture = 15    # 15장으로 조정
        last_capture_time = 0
        capture_interval = 0.13 # 2초 내외로 15장 수집 가능 (0.13 * 15 = 1.95s)

        logger.info(f"[FACE_THREAD] Starting auth capture (Target: {max_capture} frames in ~2s)")

        while self._running and len(face_imgs) < max_capture:
            frame = get_frame()
            if frame is None:
                self.msleep(10)
                continue

            now = time.time()
            if deadline is None:
                deadline = now + AUTH_TIMEOUT_SEC
            if now > deadline:
                logger.warning("[FACE_THREAD] Auth timeout during capture")
                break

            self.frame_ready.emit(frame.copy())

            if now - last_capture_time > capture_interval:
                # 검출은 저해상도로 빠르게 (BGR 그대로 전달 — detect_face가 내부에서 BGR→RGB 변환)
                small_frame = cv2.resize(frame, (320, 240))
                faces = detect_face(small_frame)

                if faces:
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx*2, sy*2, sw*2, sh*2

                    face_bgr = frame[max(0,y):min(480,y+h), max(0,x):min(640,x+w)]
                    if face_bgr.size > 0:
                        # 등록과 동일한 BGR 포맷으로 저장 (임베딩 색공간 일치)
                        face_imgs.append(face_bgr)
                        last_capture_time = now
                        logger.debug(f"[AUTH_CAPTURE] Progress: {len(face_imgs)}/{max_capture}")

            self.msleep(5)

        if self._running:
            if face_imgs:
                logger.info(f"[FACE_THREAD] Capture done. Total {len(face_imgs)} frames collected.")
                self.capture_done.emit(face_imgs)
            else:
                self.auth_failed.emit()

    # ─────────────────────────────── register ────────────────────────────────

    def _run_register(self):
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        import cv2
        face_imgs = []
        frame_count = 0
        last_capture_time = 0.0
        phase_idx = 0

        self.phase_changed.emit(0, _PHASES[0])

        while self._running and len(face_imgs) < _REGISTER_TARGET:
            frame = get_frame()
            if frame is None:
                self.msleep(10)
                continue

            self.frame_ready.emit(frame.copy())
            frame_count += 1

            now = time.time()
            if now - last_capture_time < _REGISTER_COOLDOWN_SEC:
                self.msleep(1)
                continue

            small_frame = cv2.resize(frame, (320, 240))
            faces = detect_face(small_frame)

            if faces:
                sx, sy, sw, sh = faces[0]
                x, y, w, h = sx*2, sy*2, sw*2, sh*2

                fh, fw = frame.shape[:2]
                mx, my = int(w * _FACE_MARGIN), int(h * _FACE_MARGIN)
                x1, y1 = max(0, x - mx), max(0, y - my)
                x2, y2 = min(fw, x + w + mx), min(fh, y + h + my)

                crop = frame[y1:y2, x1:x2]
                if crop.size > 0:
                    face_imgs.append(crop)
                    last_capture_time = now
                    self.capture_progress.emit(len(face_imgs))
                    logger.debug(f"[REGISTER] Captured {len(face_imgs)}/20  phase={_PHASES[phase_idx]}")

                    # 이 페이즈에서 _PHOTOS_PER_PHASE장 완료 → 다음 방향으로 전환
                    next_phase = len(face_imgs) // _PHOTOS_PER_PHASE
                    if next_phase != phase_idx and next_phase < len(_PHASES):
                        phase_idx = next_phase
                        # 카운트다운 (2→1) 후 다음 방향 안내
                        for countdown in range(int(_PHASE_PAUSE_SEC), 0, -1):
                            if not self._running:
                                break
                            self.phase_changed.emit(-countdown, _PHASES[phase_idx])
                            self.msleep(1000)
                        if self._running:
                            self.phase_changed.emit(phase_idx, _PHASES[phase_idx])
                        last_capture_time = time.time()

            self.msleep(1)

        if self._running:
            self.capture_done.emit(face_imgs)
