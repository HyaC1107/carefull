from PyQt5.QtCore import QThread, pyqtSignal

from camera.camera import get_frame
from face_detection.mediapipe_detector import detect_face
from auth.authenticate import authenticate

MODE_AUTH = "auth"
MODE_REGISTER = "register"

_REGISTER_TARGET = 20
_REGISTER_INTERVAL_MS = 500
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
        if self._mode == MODE_AUTH:
            self._run_auth()
        else:
            self._run_register()

    def stop(self):
        self._running = False

    # ──────────────────────────────── auth ───────────────────────────────────

    def _run_auth(self):
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
        face_imgs = []

        while self._running and len(face_imgs) < _REGISTER_TARGET:
            frame = get_frame()
            if frame is None:
                self.msleep(100)
                continue

            self.frame_ready.emit(frame.copy())

            faces = detect_face(frame)
            if not faces:
                self.msleep(100)
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
            self.capture_progress.emit(len(face_imgs))
            self.msleep(_REGISTER_INTERVAL_MS)

        if self._running:
            self.capture_done.emit(face_imgs)
