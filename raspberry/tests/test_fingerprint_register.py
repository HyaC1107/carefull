"""
지문 등록 단독 테스트
  실행: python -m tests.test_fingerprint_register  (raspberry/ 루트에서)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QLabel, QMainWindow, QStackedWidget,
    QVBoxLayout, QWidget, QPushButton,
)

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN
from ui.screens.fingerprint_register import FingerprintRegisterScreen


class _SimpleResultScreen(QWidget):
    def __init__(self, on_retry, parent=None):
        super().__init__(parent)
        self._on_retry = on_retry
        self.setStyleSheet("background: #dcfce7;")
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(32)

        status = QLabel("등록 완료")
        status.setFont(QFont("Sans Serif", 70, QFont.Bold))
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #16a34a;")
        lay.addWidget(status)

        btn = QPushButton("다시 등록")
        btn.setMinimumHeight(70)
        btn.setMinimumWidth(300)
        btn.setFont(QFont("Sans Serif", 26))
        btn.setStyleSheet("""
            QPushButton { background: #7c3aed; color: white; border-radius: 14px; }
            QPushButton:pressed { background: #6d28d9; }
        """)
        btn.clicked.connect(self._on_retry)
        lay.addWidget(btn, alignment=Qt.AlignCenter)


class _MockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("지문 등록 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session = {}

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._fp_reg = FingerprintRegisterScreen(self)
        self._result = _SimpleResultScreen(on_retry=self._go_register, parent=self)

        self.screens = {
            "fingerprint_register": self._fp_reg,
            "register_complete":    self._result,
            # 등록 후 홈으로 가려는 시도도 결과 화면으로 대체
            "home":                 self._result,
        }
        self.stack.addWidget(self._fp_reg)
        self.stack.addWidget(self._result)

        self._go_register()

    def show_screen(self, name: str):
        screen = self.screens.get(name)
        if screen:
            self.stack.setCurrentWidget(screen)

    def _go_register(self):
        self.show_screen("fingerprint_register")


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
