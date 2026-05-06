"""
얼굴 인증 단독 테스트
  - 얼굴 인증 성공/실패 후 지문 화면으로 넘어가지 않고 결과만 출력
  - 실행: python -m tests.test_face_auth  (raspberry/ 루트에서)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN
from ui.screens.camera_view import CameraViewScreen
from ui.threads.face_thread import MODE_AUTH


class _ResultScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(24)

        self._msg = QLabel()
        self._msg.setFont(QFont("Sans Serif", 36, QFont.Bold))
        self._msg.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._msg)

        self._sub = QLabel()
        self._sub.setFont(QFont("Sans Serif", 24))
        self._sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._sub)

        btn = QPushButton("다시 테스트")
        btn.setMinimumHeight(60)
        btn.setFont(QFont("Sans Serif", 22))
        btn.setStyleSheet("""
            QPushButton { background: #3b82f6; color: white; border-radius: 12px; }
            QPushButton:pressed { background: #2563eb; }
        """)
        btn.clicked.connect(lambda: self._app.show_screen("camera_view"))
        lay.addWidget(btn)

    def set_result(self, success: bool, user: str = "", score: float = 0.0):
        if success:
            self.setStyleSheet("background: #dcfce7;")
            self._msg.setText("인증 성공")
            self._msg.setStyleSheet("color: #16a34a;")
            self._sub.setText(f"유사도: {score:.3f}")
        else:
            self.setStyleSheet("background: #fee2e2;")
            self._msg.setText("인증 실패")
            from ui.screens.camera_view import CameraViewScreen, _AuthWorker, _EmbeddingSaveWorker
            from ui.threads.face_thread import FaceThread, MODE_AUTH, _is_centered

            import cv2
            import numpy as np
            import time

            # ── 테스트용 개선 로직 구현 ───────────────────────────────────────────────────

            class TestAuthWorker(_AuthWorker):
                """BGR->RGB 변환 및 멀티 템플릿 로직이 포함된 테스트용 워커"""
                def run(self):
                    # authenticate를 직접 호출하되, 내부에서 쓰는 모델이 RGB를 쓰도록 몽키패치하거나 
                    # 여기서 직접 모델을 제어함. 여기서는 간단히 전역 모델의 predict를 패치함.
                    from face_recognition.model_loader import get_model
                    model = get_model()
                    if model:
                        original_predict = model.predict
                        def test_predict(face_img):
                            rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                            return original_predict(rgb)
                        model.predict = test_predict

                    super().run()

                    if model:
                        model.predict = original_predict # 원복


            class TestFaceThread(FaceThread):
                """정사각형 크롭 로직이 적용된 테스트용 스레드"""
                def _run_auth(self):
                    from camera.camera import get_frame
                    from face_detection.mediapipe_detector import detect_face
                    from hardware.gimbal import Gimbal
                    import cv2

                    gimbal = Gimbal()
                    face_imgs = []
                    max_capture = 15
                    last_capture_time = 0.0
                    capture_interval = 0.13
                    consecutive_face_count = 0

                    try:
                        while self._running and len(face_imgs) < max_capture:
                            frame = get_frame()
                            if frame is None: continue

                            fh, fw = frame.shape[:2]
                            self.frame_ready.emit(frame.copy())
                            now = time.time()

                            if now - last_capture_time > capture_interval:
                                small_frame = cv2.resize(frame, (320, 240))
                                faces = detect_face(small_frame)

                                if faces:
                                    consecutive_face_count += 1
                                    sx, sy, sw, sh = faces[0]
                                    x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
                                    if consecutive_face_count >= 2:
                                        gimbal.track_face((x, y, w, h), fw, fh)

                                    if _is_centered((x, y, w, h), fw):
                                        # 개선된 정사각형 크롭
                                        cx, cy = x + w / 2, y + h / 2
                                        side = max(w, h) * 1.45
                                        x1, y1 = int(max(0, cx-side/2)), int(max(0, cy-side/2))
                                        x2, y2 = int(min(fw, cx+side/2)), int(min(fh, cy+side/2))
                                        face_bgr = frame[y1:y2, x1:x2]
                                        if face_bgr.size > 0:
                                            face_imgs.append(face_bgr)
                                            last_capture_time = now
                                else:
                                    consecutive_face_count = 0
                                    gimbal.update_idle()
                            self.msleep(5)
                    finally:
                        gimbal.stop()
                    if self._running:
                        if face_imgs: self.capture_done.emit(face_imgs)
                        else: self.auth_failed.emit()


            class TestCameraViewScreen(CameraViewScreen):
                """테스트용 스레드와 워커를 사용하도록 오버라이드"""
                def _start_thread(self):
                    super()._stop_thread()
                    self._frame_count = 0
                    self._auth_started = False
                    self._loading_lbl.show()
                    # 테스트용 스레드 사용
                    self._thread = TestFaceThread(mode=self._mode)
                    self._thread.frame_ready.connect(self._on_frame_ready)
                    self._thread.capture_done.connect(self._on_capture_done)
                    self._thread.auth_failed.connect(self._on_auth_failed)
                    self._thread.start()

                def _on_capture_done(self, face_imgs: list):
                    self._stop_thread()
                    if self._mode == MODE_AUTH:
                        self._processing_overlay.show()
                        # 테스트용 워커 사용
                        self._auth_worker = TestAuthWorker(face_imgs, parent=self)
                        self._auth_worker.success.connect(self._on_auth_success)
                        self._auth_worker.failed.connect(self._on_auth_failed)
                        self._auth_worker.start()
                    else:
                        super()._on_capture_done(face_imgs)


            class _MockApp(QMainWindow):
                """얼굴 인증 단독 테스트용 최소 앱 — 지문 화면 없음."""

                def __init__(self):
                    super().__init__()
                    self.setWindowTitle("얼굴 인증 테스트 (개선 로직 적용)")
                    self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

                    self.current_session = {
                        "face_verified": False,
                        "similarity_score": 0.0,
                    }

                    self.stack = QStackedWidget()
                    self.setCentralWidget(self.stack)

                    # 테스트용 스크린 사용
                    cam = TestCameraViewScreen(self)
                    cam.set_mode(MODE_AUTH)
                    result = _ResultScreen(self)

                    self.screens = {
                        "camera_view": cam,
                        "auth_result":  result,
                        "fingerprint_auth": result,
                    }


        for s in self.screens.values():
            if s not in [self.stack.widget(i) for i in range(self.stack.count())]:
                self.stack.addWidget(s)

        self.show_screen("camera_view")

    def show_screen(self, name: str):
        screen = self.screens.get(name)
        if screen is None:
            return

        # 지문 폴백 요청 시 실패 결과로 처리
        if name == "fingerprint_auth":
            score = self.current_session.get("similarity_score", 0.0)
            self.screens["auth_result"].set_result(success=False, score=score)
            self.stack.setCurrentWidget(self.screens["auth_result"])
            return

        # 성공 시 결과 업데이트
        if name == "auth_result":
            score = self.current_session.get("similarity_score", 0.0)
            # CameraViewScreen에서 성공 시 세션에 점수를 담아둠
            self.screens["auth_result"].set_result(success=True, score=score)

        self.stack.setCurrentWidget(screen)

        if name == "camera_view":
            self.current_session["face_verified"] = False
            self.current_session["similarity_score"] = 0.0


def main():
    app = QApplication(sys.argv)
    window = _MockApp()
    if FULLSCREEN:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
