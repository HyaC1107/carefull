"""
지문 인증 단독 테스트
  - 지문 인증 성공/실패 후 결과만 출력
  - 실행: python -m tests.test_fingerprint_auth  (raspberry/ 루트에서)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN
from ui.screens.fingerprint_auth import FingerprintAuthScreen


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
        btn.clicked.connect(lambda: self._app.show_screen("fingerprint_auth"))
        lay.addWidget(btn)

    def set_result(self, success: bool, fingerprint: bool = False):
        if success:
            self.setStyleSheet("background: #dcfce7;")
            self._msg.setText("인증 성공")
            self._msg.setStyleSheet("color: #16a34a;")
            self._sub.setText("지문 인증 완료")
        else:
            self.setStyleSheet("background: #fee2e2;")
            self._msg.setText("인증 실패")
            self._msg.setStyleSheet("color: #dc2626;")
            self._sub.setText("지문 인증 타임아웃")


class _MockApp(QMainWindow):
    """지문 인증 단독 테스트용 최소 앱."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("지문 인증 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session = {
            "face_verified": False,
            "similarity_score": 0.0,
        }

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        fp = FingerprintAuthScreen(self)
        result = _ResultScreen(self)

        self.screens = {
            "fingerprint_auth": fp,
            "auth_result":      result,
        }

        for s in self.screens.values():
            self.stack.addWidget(s)

        self.show_screen("fingerprint_auth")

    def show_screen(self, name: str):
        screen = self.screens.get(name)
        if screen is None:
            return
        self.stack.setCurrentWidget(screen)


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
