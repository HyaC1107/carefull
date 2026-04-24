import time

from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE

MODE_AUTH = "auth"
MODE_REGISTER = "register"

_REGISTER_TARGET = 20
_REGISTER_COOLDOWN_SEC = 0.5   # 캡처 간격 (블로킹 sleep 대신 타임스탬프로 관리)
_DETECT_EVERY_N = 3            # N프레임마다 1번 AI 검출 (~30fps 기준 10fps 검출)
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
                self.auth_success.emit("테스트유저", 0.99)
        else:
            for i in range(1, _REGISTER_TARGET + 1):
                if not self._running:
                    return
                self.capture_progress.emit(i)
                self.msleep(100)
            if self._running:
                self.capture_done.emit([])

    def stop(self):
        self._running = False

    # ──────────────────────────────── auth ───────────────────────────────────

    def _run_auth(self):
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        from auth.authenticate import authenticate
        retries = 0
        while self._running and retries < self._max_retries:
            frame = get_frame()
            if frame is None:
                retries += 1
                self.msleep(300)
                continue

            self.frame_ready.emit(frame.copy())

            faces = detect_face(frame)
            if not faces:
                retries += 1
                self.msleep(300)
                continue

            x, y, w, h = faces[0]
            face_img = frame[y: y + h, x: x + w]
            if face_img.size == 0:
                retries += 1
                continue

            user, score = authenticate(face_img)
            if user:
                if self._running:
                    self.auth_success.emit(user, float(score))
                return

            retries += 1
            self.msleep(500)

        if self._running:
            self.auth_failed.emit()

    # ─────────────────────────────── register ────────────────────────────────

    def _run_register(self):
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        face_imgs = []
        frame_count = 0
        last_capture_time = 0.0

        while self._running and len(face_imgs) < _REGISTER_TARGET:
            frame = get_frame()
            if frame is None:
                self.msleep(30)
                continue

            # 항상 프레임 송출 → 디스플레이 ~30fps 유지
            self.frame_ready.emit(frame.copy())
            frame_count += 1
            self.msleep(33)

            # N프레임마다 + 캡처 쿨다운 지난 경우에만 AI 검출
            now = time.time()
            if frame_count % _DETECT_EVERY_N != 0:
                continue
            if now - last_capture_time < _REGISTER_COOLDOWN_SEC:
                continue

            faces = detect_face(frame)
            if not faces:
                continue

            x, y, w, h = faces[0]
            fh, fw = frame.shape[:2]
            mx = int(w * _FACE_MARGIN)
            my = int(h * _FACE_MARGIN)
            x1 = max(0, x - mx)
            y1 = max(0, y - my)
            x2 = min(fw, x + w + mx)
            y2 = min(fh, y + h + my)

            crop = frame[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            face_imgs.append(crop)
            last_capture_time = now
            self.capture_progress.emit(len(face_imgs))

        if self._running:
            self.capture_done.emit(face_imgs)
