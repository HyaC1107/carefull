import time
import logging

from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE

logger = logging.getLogger(__name__)

MODE_AUTH = "auth"
MODE_REGISTER = "register"

AUTH_TIMEOUT_SEC = 7           # 얼굴 인증 최대 시도 시간 (초과 시 지문 폴백)
_REGISTER_TARGET = 20
_REGISTER_COOLDOWN_SEC = 0.5   # 캡처 간격 (블로킹 sleep 대신 타임스탬프로 관리)
_DETECT_EVERY_N = 8            # N프레임마다 1번 AI 검출 (~30fps 기준 약 4fps 검출)
_FACE_MARGIN = 0.2


class FaceThread(QThread):
    frame_ready = pyqtSignal(object)       # BGR ndarray
    auth_success = pyqtSignal(str, float)  # matched user name, similarity score
    auth_failed = pyqtSignal()
    capture_progress = pyqtSignal(int)     # captured count (register mode)
    capture_done = pyqtSignal(list)        # list of face BGR images (register mode)

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

    # ──────────────────────────────── auth ───────────────────────────────────

    def _run_auth(self):
        """
        [변경] 실시간 추론 대신 3초 동안 얼굴 프레임을 수집만 함.
        수집 완료 후 capture_done 시그널로 프레임 리스트 전달.
        """
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        import cv2

        deadline = None
        start_time = time.time()
        face_imgs = []
        max_capture = 10  # 인증용으로 수집할 최대 프레임 수
        last_capture_time = 0
        capture_interval = 0.3 # 0.3초마다 1장씩

        logger.info("[FACE_THREAD] Starting auth capture (3s window)")

        while self._running and len(face_imgs) < max_capture:
            frame = get_frame()
            if frame is None:
                self.msleep(10)
                continue

            now = time.time()
            if deadline is None:
                deadline = now + AUTH_TIMEOUT_SEC
            if now > deadline:
                break

            # 화면 갱신은 계속함
            self.frame_ready.emit(frame.copy())

            # AI용 저해상도 검출
            if now - last_capture_time > capture_interval:
                small_frame = cv2.resize(frame, (320, 240))
                faces = detect_face(small_frame)
                
                if faces:
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx*2, sy*2, sw*2, sh*2
                    
                    face_img = frame[max(0,y):min(480,y+h), max(0,x):min(640,x+w)]
                    if face_img.size > 0:
                        face_imgs.append(face_img)
                        last_capture_time = now
                        logger.debug(f"[AUTH_CAPTURE] Collected {len(face_imgs)}/{max_capture}")

            self.msleep(10)

        if self._running:
            if face_imgs:
                logger.info(f"[FACE_THREAD] Capture done. Total: {len(face_imgs)}")
                self.capture_done.emit(face_imgs)
            else:
                logger.info("[FACE_THREAD] No face captured during timeout")
                self.auth_failed.emit()

    # ─────────────────────────────── register ────────────────────────────────

    def _run_register(self):
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        import cv2
        face_imgs = []
        frame_count = 0
        last_capture_time = 0.0

        while self._running and len(face_imgs) < _REGISTER_TARGET:
            frame = get_frame()
            if frame is None:
                self.msleep(10)
                continue

            # 항상 프레임 송출 (등록 시에도 부드럽게)
            self.frame_ready.emit(frame.copy())
            frame_count += 1

            now = time.time()
            if now - last_capture_time < _REGISTER_COOLDOWN_SEC:
                self.msleep(1)
                continue

            # 등록 시에도 검출 속도 향상을 위해 저해상도 사용
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
                    logger.debug(f"[REGISTER] Captured {len(face_imgs)}/20")

            self.msleep(1)

        if self._running:
            self.capture_done.emit(face_imgs)
