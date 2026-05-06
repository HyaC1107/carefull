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
_PHASE_PAUSE_SEC = 2.0
_CENTER_TOL = 0.15   # 얼굴 수평 중심이 프레임 중심에서 ±15% 이내일 때만 캡처 (좌우 1축 서보 기준)


def _is_centered(face, fw: int) -> bool:
    """얼굴 수평 중심이 프레임 중앙 ±_CENTER_TOL 범위 안에 있는지 확인 (수직은 무시)."""
    x, y, w, h = face
    cx = x + w / 2
    return abs(cx - fw / 2) < fw * _CENTER_TOL


class FaceThread(QThread):
    frame_ready = pyqtSignal(object)       # BGR ndarray
    auth_success = pyqtSignal(str, float)  # matched user name, similarity score
    auth_failed = pyqtSignal()
    capture_progress = pyqtSignal(int)     # captured count (register mode)
    capture_done = pyqtSignal(list)        # list of face BGR images
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

    # ──────────────────────────────── auth ───────────────────────────────────

    def _run_auth(self):
        """
        배치 캡처: 최대 15장 수집 → capture_done → _AuthWorker에서 다수결 판정.
        짐벌 서보로 얼굴 추적 병행.
        """
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        from hardware.gimbal import Gimbal
        import cv2

        gimbal = Gimbal()
        deadline = None
        face_imgs = []
        max_capture = 15
        last_capture_time = 0.0
        capture_interval = 0.13   # ~2초 내 15장
        consecutive_face_count = 0

        logger.info(f"[FACE_THREAD] Starting auth capture (target: {max_capture} frames)")

        try:
            while self._running and len(face_imgs) < max_capture:
                frame = get_frame()
                if frame is None:
                    self.msleep(10)
                    continue

                fh, fw = frame.shape[:2]
                now = time.time()

                if deadline is None:
                    deadline = now + AUTH_TIMEOUT_SEC
                if now > deadline:
                    logger.warning("[FACE_THREAD] Auth timeout during capture")
                    break

                self.frame_ready.emit(frame.copy())

                if now - last_capture_time > capture_interval:
                    small_frame = cv2.resize(frame, (320, 240))
                    faces = detect_face(small_frame)   # BGR 그대로 전달

                    if faces:
                        consecutive_face_count += 1
                        sx, sy, sw, h_det = faces[0]
                        x, y, w, h = sx * 2, sy * 2, sw * 2, h_det * 2

                        # 2프레임 연속 감지 후 짐벌 추적 시작
                        if consecutive_face_count >= 2:
                            gimbal.track_face((x, y, w, h), fw, fh)

                        if _is_centered((x, y, w, h), fw):
                            # --- 고도화: 정사각형 고정 배율 크롭 (거리 편차 방지) ---
                            cx, cy = x + w / 2, y + h / 2
                            side = max(w, h) * 1.45
                            x1, y1 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
                            x2, y2 = int(min(fw, cx + side / 2)), int(min(fh, cy + side / 2))

                            face_bgr = frame[y1:y2, x1:x2]
                            if face_bgr.size > 0:
                                face_imgs.append(face_bgr)
                                last_capture_time = now
                                logger.debug(f"[AUTH_CAPTURE] {len(face_imgs)}/{max_capture}")
                    else:
                        consecutive_face_count = 0
                        gimbal.update_idle()

                self.msleep(5)

        finally:
            gimbal.stop()

        if self._running:
            if face_imgs:
                logger.info(f"[FACE_THREAD] Capture done: {len(face_imgs)} frames.")
                self.capture_done.emit(face_imgs)
            else:
                self.auth_failed.emit()

    # ─────────────────────────────── register ────────────────────────────────

    def _run_register(self):
        """
        5방향 × 4장 = 20장 등록.
        방향 전환 시 카메라 화면을 끊지 않고 안내 + 짐벌 추적 유지.
        """
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        from hardware.gimbal import Gimbal
        import cv2

        gimbal = Gimbal()
        face_imgs = []
        last_capture_time = 0.0
        phase_idx = 0
        pause_until = 0.0  # 방향 전환 대기 시간

        self.phase_changed.emit(0, _PHASES[0])

        try:
            while self._running and len(face_imgs) < _REGISTER_TARGET:
                frame = get_frame()
                if frame is None:
                    self.msleep(10)
                    continue

                # ── UX 개선: 대기 중에도 카메라 화면은 끊김 없이 송출 ──
                self.frame_ready.emit(frame.copy())

                now = time.time()
                
                # 방향 전환 대기 중이면 검출/캡처 건너뜀
                if now < pause_until:
                    self.msleep(5)
                    continue

                if now - last_capture_time < _REGISTER_COOLDOWN_SEC:
                    self.msleep(1)
                    continue

                fh, fw = frame.shape[:2]
                small_frame = cv2.resize(frame, (320, 240))
                faces = detect_face(small_frame)

                if faces:
                    faces.sort(key=lambda b: b[2] * b[3], reverse=True)
                    sx, sy, sw, h_det = faces[0]
                    x, y, w, h = sx * 2, sy * 2, sw * 2, h_det * 2

                    gimbal.track_face((x, y, w, h), fw, fh)

                    if not _is_centered((x, y, w, h), fw):
                        self.msleep(1)
                        continue

                    cx, cy = x + w / 2, y + h / 2
                    side = max(w, h) * 1.45
                    x1, y1 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
                    x2, y2 = int(min(fw, cx + side / 2)), int(min(fh, cy + side / 2))

                    crop = frame[y1:y2, x1:x2]
                    if crop.size > 0:
                        face_imgs.append(crop)
                        last_capture_time = now
                        self.capture_progress.emit(len(face_imgs))
                        logger.debug(f"[REGISTER] {len(face_imgs)}/20 phase={_PHASES[phase_idx]}")

                        # 이 페이즈 완료 → 다음 방향 안내 (비차단 대기 방식)
                        next_phase = len(face_imgs) // _PHOTOS_PER_PHASE
                        if next_phase != phase_idx and next_phase < len(_PHASES):
                            phase_idx = next_phase
                            # 카운트다운 안내 (여기서는 시각적 안내만 하고 루프는 계속 돌림)
                            self.phase_changed.emit(-2, _PHASES[phase_idx])
                            pause_until = now + _PHASE_PAUSE_SEC
                            # 1초 후 -1초 안내를 위한 스케줄링은 불가능하므로, 
                            # 단순하게 다음 루프들에서 처리하거나 단일 메시지 유지
                else:
                    gimbal.update_idle()

                self.msleep(1)

        finally:
            gimbal.stop()

        if self._running:
            self.capture_done.emit(face_imgs)
