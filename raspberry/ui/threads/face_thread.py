import time

from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE

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

        # 카메라 워밍업 시간을 인증 시간으로 소모하지 않도록
        # 첫 프레임이 도착한 시점부터 AUTH_TIMEOUT_SEC 카운트다운 시작
        deadline = None
        frame_count = 0

        while self._running:
            frame = get_frame()
            if frame is None:
                self.msleep(30)
                continue

            if deadline is None:
                deadline = time.time() + AUTH_TIMEOUT_SEC
            if time.time() > deadline:
                break

            # 항상 화면 갱신 시그널을 먼저 보냄
            self.frame_ready.emit(frame.copy())
            frame_count += 1

            # N프레임마다 한 번씩만 AI 연산 수행
            if frame_count % _DETECT_EVERY_N != 0:
                self.msleep(10) # CPU 부하 감소를 위한 짧은 휴식
                continue

            faces = detect_face(frame)
            if not faces:
                continue

            x, y, w, h = faces[0]
            face_img = frame[y: y + h, x: x + w]
            if face_img.size == 0:
                continue

            user, score = authenticate(face_img)
            if user:
                if self._running:
                    self.auth_success.emit(user, float(score))
                return

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
