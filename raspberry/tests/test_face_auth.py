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
            self._msg.setStyleSheet("color: #dc2626;")
            self._sub.setText("얼굴 인증 타임아웃")


class _MockApp(QMainWindow):
    """얼굴 인증 단독 테스트용 최소 앱 — 지문 화면 없음."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("얼굴 인증 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session = {
            "face_verified": False,
            "similarity_score": 0.0,
        }

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        cam = CameraViewScreen(self)
        cam.set_mode(MODE_AUTH)
        result = _ResultScreen(self)

        self.screens = {
            "camera_view": cam,
            "auth_result":  result,
            # 지문 화면 요청이 와도 결과 화면으로 대체
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
            self.screens["auth_result"].set_result(success=False)
            self.stack.setCurrentWidget(self.screens["auth_result"])
            return

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
