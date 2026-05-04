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
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        from auth.authenticate import authenticate

        deadline = None
        frame_count = 0
        inference_count = 0
        start_time = time.time()
        
        # AI 상태 관리
        is_ai_busy = False
        last_ai_time = 0
        ai_interval = 0.3  # AI 연산 간격 (초)

        while self._running:
            frame = get_frame()
            if frame is None:
                self.msleep(10)
                continue

            now = time.time()
            if deadline is None:
                deadline = now + AUTH_TIMEOUT_SEC
                
            if now > deadline:
                logger.info(f"[FACE_THREAD] Auth timeout reached ({AUTH_TIMEOUT_SEC}s)")
                break

            # 1. 화면 갱신은 어떤 경우에도 멈추지 않음 (High FPS 유지)
            self.frame_ready.emit(frame.copy())
            frame_count += 1

            # 2. AI 연산 조건 체크 (진행 중이 아니고, 간격이 지났을 때만)
            if not is_ai_busy and (now - last_ai_time > ai_interval):
                # AI 로직을 블로킹 없이 실행하기 위해 별도의 처리가 필요하지만,
                # Python 스레드 특성상 루프 안에서 실행하되, 
                # 이번 루프에서 AI를 수행하더라도 다음 루프는 즉시 돌아가게끔 구조화는 어려우므로
                # 연산 자체를 최적화하여 멈춤 현상을 최소화함
                
                is_ai_busy = True
                inference_count += 1
                
                # AI용 저해상도 복사본 생성 (속도 향상 핵심)
                small_frame = cv2.resize(frame, (320, 240))
                
                t1 = time.time()
                # 1. Face Detection (저해상도에서 수행)
                faces = detect_face(small_frame)
                det_time = time.time() - t1
                
                if faces:
                    # 검출된 좌표를 원본 해상도로 복구
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx*2, sy*2, sw*2, sh*2
                    
                    face_img = frame[max(0,y):min(480,y+h), max(0,x):min(640,x+w)]
                    
                    if face_img.size > 0:
                        t2 = time.time()
                        # 2. Face Authentication
                        user, score = authenticate(face_img)
                        auth_time = time.time() - t2
                        
                        logger.debug(f"[AUTH] Det: {det_time*1000:.1f}ms, Auth: {auth_time*1000:.1f}ms, Score: {score:.4f}")

                        if user:
                            total_dur = time.time() - start_time
                            avg_fps = frame_count / total_dur
                            logger.info(f"[FACE_THREAD] Auth Success: {user} (Score: {score:.4f})")
                            logger.info(f"  - Total Frames: {frame_count}, Avg FPS: {avg_fps:.1f}")
                            
                            if self._running:
                                self.auth_success.emit(user, float(score))
                            return

                last_ai_time = time.time()
                is_ai_busy = False

            # CPU 점유율을 너무 높이지 않기 위해 아주 짧은 휴식
            self.msleep(1)

        total_dur = time.time() - start_time
        avg_fps = frame_count / total_dur if total_dur > 0 else 0
        logger.info(f"[FACE_THREAD] Auth Finished. Frames: {frame_count}, Avg FPS: {avg_fps:.1f}")
        
        if self._running:
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
