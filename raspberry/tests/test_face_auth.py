"""
얼굴 인증 단독 테스트 (최종 개선 로직 반영 버전)
  - 로직: BGR->RGB 변환, 정사각형 크롭, 멀티 템플릿(10개) 대응
  - 기능: 실시간 점수 확인, 거리별 편차 테스트 전용
  - 실행: python -m tests.test_face_auth (raspberry/ 루트에서)
"""
import sys
import os
import cv2
import numpy as np
import time

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN, FACE_MATCH_THRESHOLD
from ui.screens.camera_view import CameraViewScreen, _AuthWorker
from ui.threads.face_thread import FaceThread, MODE_AUTH, _is_centered

# ── 1. 테스트용 개선 로직 구현 ───────────────────────────────────────────────────

class TestAuthWorker(_AuthWorker):
    """BGR->RGB 변환 및 멀티 템플릿 로직이 포함된 테스트용 워커"""
    def run(self):
        from face_recognition.model_loader import get_model
        model = get_model()
        if model:
            # 실구동 모델의 predict를 가로채서 BGR->RGB 변환 강제 적용
            original_predict = model.predict
            def test_predict(face_img):
                # 이미 RGB인 경우 대비 (일부 로직에서 이미 변환했을 수 있음)
                rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                return original_predict(rgb)
            model.predict = test_predict
        
        try:
            print("[TEST_AUTH] Starting inference with RGB conversion and Multi-Template support...")
            super().run()
        finally:
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
        
        print("[TEST_THREAD] Auth capture started with Square-Crop logic.")

        try:
            while self._running and len(face_imgs) < max_capture:
                frame = get_frame()
                if frame is None:
                    self.msleep(10)
                    continue

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
                            # 개선된 정사각형 크롭 (거리 편차 감소 핵심 로직)
                            cx, cy = x + w / 2, y + h / 2
                            side = max(w, h) * 1.45
                            x1, y1 = int(max(0, cx - side / 2)), int(max(0, cy - side / 2))
                            x2, y2 = int(min(fw, cx + side / 2)), int(min(fh, cy + side / 2))
                            
                            face_bgr = frame[y1:y2, x1:x2]
                            if face_bgr.size > 0:
                                face_imgs.append(face_bgr)
                                last_capture_time = now
                                print(f"[TEST_CAPTURE] {len(face_imgs)}/{max_capture} cropped to {face_bgr.shape}")
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
    """테스트 전용 Thread/Worker를 사용하도록 확장된 스크린"""
    def _start_thread(self):
        self._stop_thread()
        self._frame_count = 0
        self._auth_started = False
        self._loading_lbl.show()
        # 테스트 전용 스레드 주입
        self._thread = TestFaceThread(mode=self._mode)
        self._thread.frame_ready.connect(self._on_frame_ready)
        self._thread.capture_done.connect(self._on_capture_done)
        if self._mode == MODE_AUTH:
            self._thread.auth_failed.connect(self._on_auth_failed)
        self._thread.start()

    def _on_capture_done(self, face_imgs: list):
        self._stop_thread()
        if self._mode == MODE_AUTH:
            self._processing_overlay.show()
            # 테스트 전용 워커 주입
            self._auth_worker = TestAuthWorker(face_imgs, parent=self)
            self._auth_worker.success.connect(self._on_auth_success)
            self._auth_worker.failed.connect(self._on_auth_failed)
            self._auth_worker.start()
        else:
            super()._on_capture_done(face_imgs)


# ── 2. 결과 표시 및 메인 앱 구조 ───────────────────────────────────────────────────

class _ResultScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(30)

        self._msg = QLabel()
        self._msg.setFont(QFont("Sans Serif", 48, QFont.Bold))
        self._msg.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._msg)

        self._score_lbl = QLabel()
        self._score_lbl.setFont(QFont("Sans Serif", 32))
        self._score_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._score_lbl)

        self._detail_lbl = QLabel()
        self._detail_lbl.setFont(QFont("Sans Serif", 22))
        self._detail_lbl.setAlignment(Qt.AlignCenter)
        self._detail_lbl.setStyleSheet("color: #64748b;")
        lay.addWidget(self._detail_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        
        btn_retry = QPushButton("다시 테스트")
        btn_retry.setMinimumHeight(80)
        btn_retry.setFixedWidth(300)
        btn_retry.setFont(QFont("Sans Serif", 26, QFont.Bold))
        btn_retry.setStyleSheet("""
            QPushButton { background: #3b82f6; color: white; border-radius: 15px; }
            QPushButton:pressed { background: #2563eb; }
        """)
        btn_retry.clicked.connect(lambda: self._app.show_screen("camera_view"))
        
        btn_quit = QPushButton("종료")
        btn_quit.setMinimumHeight(80)
        btn_quit.setFixedWidth(200)
        btn_quit.setFont(QFont("Sans Serif", 26, QFont.Bold))
        btn_quit.setStyleSheet("""
            QPushButton { background: #64748b; color: white; border-radius: 15px; }
            QPushButton:pressed { background: #475569; }
        """)
        btn_quit.clicked.connect(QApplication.quit)
        
        btn_row.addStretch()
        btn_row.addWidget(btn_retry)
        btn_row.addWidget(btn_quit)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def set_result(self, success: bool, score: float = 0.0):
        if success:
            self.setStyleSheet("background: #f0fdf4;")
            self._msg.setText("인증 성공 ✅")
            self._msg.setStyleSheet("color: #16a34a;")
        else:
            self.setStyleSheet("background: #fef2f2;")
            self._msg.setText("인증 실패 ❌")
            self._msg.setStyleSheet("color: #dc2626;")
            
        self._score_lbl.setText(f"최종 유사도: {score:.4f}")
        self._detail_lbl.setText(f"설정된 임계값(Threshold): {FACE_MATCH_THRESHOLD}")


class _MockApp(QMainWindow):
    """테스트용 가상 메인 앱"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Carefull Face Auth Test Lab")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session = {
            "face_verified": False,
            "similarity_score": 0.0,
        }

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # 개선 로직이 적용된 테스트 스크린 사용
        self.cam = TestCameraViewScreen(self)
        self.cam.set_mode(MODE_AUTH)
        self.result = _ResultScreen(self)

        self.stack.addWidget(self.cam)
        self.stack.addWidget(self.result)

        self.show_screen("camera_view")

    def show_screen(self, name: str):
        if name == "camera_view":
            self.current_session["face_verified"] = False
            self.current_session["similarity_score"] = 0.0
            self.stack.setCurrentWidget(self.cam)
        elif name == "auth_result":
            score = self.current_session.get("similarity_score", 0.0)
            self.result.set_result(success=True, score=score)
            self.stack.setCurrentWidget(self.result)
        elif name == "fingerprint_auth":
            # 실패 시 지문 화면 대신 결과 화면 표시
            score = self.current_session.get("similarity_score", 0.0)
            self.result.set_result(success=False, score=score)
            self.stack.setCurrentWidget(self.result)


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
