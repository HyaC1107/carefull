"""
지문 인증 단독 테스트 — 성공/실패 여부만 표시
  실행: python -m tests.test_fingerprint_auth  (raspberry/ 루트에서)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QLabel, QMainWindow, QStackedWidget,
    QVBoxLayout, QWidget, QPushButton,
)

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN
from ui.screens.fingerprint_auth import FingerprintAuthScreen


class _SimpleResultScreen(QWidget):
    def __init__(self, on_retry, parent=None):
        super().__init__(parent)
        self._on_retry = on_retry
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(32)

        self._status_lbl = QLabel()
        self._status_lbl.setFont(QFont("Sans Serif", 80, QFont.Bold))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._status_lbl)

        btn = QPushButton("다시 테스트")
        btn.setMinimumHeight(70)
        btn.setMinimumWidth(300)
        btn.setFont(QFont("Sans Serif", 26))
        btn.setStyleSheet("""
            QPushButton { background: #3b82f6; color: white; border-radius: 14px; }
            QPushButton:pressed { background: #2563eb; }
        """)
        btn.clicked.connect(self._retry)
        lay.addWidget(btn, alignment=Qt.AlignCenter)

    def set_result(self, success: bool, **kwargs):
        if success:
            self.setStyleSheet("background: #dcfce7;")
            self._status_lbl.setText("성공")
            self._status_lbl.setStyleSheet("color: #16a34a;")
        else:
            self.setStyleSheet("background: #fee2e2;")
            self._status_lbl.setText("실패")
            self._status_lbl.setStyleSheet("color: #dc2626;")

    def _retry(self):
        self._on_retry()


class _MockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("지문 인증 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session = {"face_verified": False, "similarity_score": 0.0}

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._result = _SimpleResultScreen(on_retry=self._go_auth, parent=self)
        self._fp_auth = FingerprintAuthScreen(self)

        self.screens = {
            "fingerprint_auth": self._fp_auth,
            "auth_result":      self._result,
        }
        self.stack.addWidget(self._fp_auth)
        self.stack.addWidget(self._result)

        self._go_auth()

    def show_screen(self, name: str):
        screen = self.screens.get(name)
        if screen:
            self.stack.setCurrentWidget(screen)

    def _go_auth(self):
        self.show_screen("fingerprint_auth")


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
