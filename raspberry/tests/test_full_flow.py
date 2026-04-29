"""
복약 전체 플로우 통합 테스트
  실행: python -m tests.test_full_flow  (raspberry/ 루트에서)

플로우: 얼굴 인증 → 지문 인증 폴백 → 인증 완료 → 약 배출 → 복약 → 완료
각 단계를 순서대로 이동하며 전체 화면 전환이 정상 동작하는지 확인한다.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QStackedWidget, QVBoxLayout, QWidget,
)

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN
from ui.screens.camera_view import CameraViewScreen
from ui.screens.fingerprint_auth import FingerprintAuthScreen
from ui.screens.auth_result import AuthResultScreen
from ui.screens.dispensing import DispensingScreen
from ui.screens.medication import MedicationScreen
from ui.screens.complete import CompleteScreen


_SCREEN_ORDER = [
    "camera_view",
    "fingerprint_auth",
    "auth_result",
    "dispensing",
    "medication",
    "complete",
]

_SCREEN_LABELS = {
    "camera_view":      "얼굴 인증",
    "fingerprint_auth": "지문 인증",
    "auth_result":      "인증 완료",
    "dispensing":       "약 배출 중",
    "medication":       "복약해주세요",
    "complete":         "완료",
}


class _NavBar(QWidget):
    def __init__(self, on_prev, on_next, on_home, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(16)

        prev_btn = QPushButton("← 이전")
        prev_btn.setFont(QFont("Sans Serif", 20))
        prev_btn.setMinimumHeight(56)
        prev_btn.setStyleSheet("""
            QPushButton { background: white; color: #374151; border: 2px solid #d1d5db; border-radius: 10px; padding: 0 18px; }
            QPushButton:pressed { background: #f3f4f6; }
        """)
        prev_btn.clicked.connect(on_prev)
        lay.addWidget(prev_btn)

        self._step_lbl = QLabel()
        self._step_lbl.setFont(QFont("Sans Serif", 20))
        self._step_lbl.setAlignment(Qt.AlignCenter)
        self._step_lbl.setStyleSheet("color: #6b7280;")
        lay.addWidget(self._step_lbl, stretch=1)

        next_btn = QPushButton("다음 →")
        next_btn.setFont(QFont("Sans Serif", 20))
        next_btn.setMinimumHeight(56)
        next_btn.setStyleSheet("""
            QPushButton { background: #3b82f6; color: white; border-radius: 10px; padding: 0 18px; }
            QPushButton:pressed { background: #2563eb; }
        """)
        next_btn.clicked.connect(on_next)
        lay.addWidget(next_btn)

        home_btn = QPushButton("홈")
        home_btn.setFont(QFont("Sans Serif", 20))
        home_btn.setMinimumHeight(56)
        home_btn.setStyleSheet("""
            QPushButton { background: #f97316; color: white; border-radius: 10px; padding: 0 18px; }
            QPushButton:pressed { background: #ea580c; }
        """)
        home_btn.clicked.connect(on_home)
        lay.addWidget(home_btn)

    def set_step(self, idx: int, total: int, label: str):
        self._step_lbl.setText(f"[{idx + 1}/{total}] {label}")


class _MockApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("전체 플로우 통합 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session = {
            "face_verified": False,
            "similarity_score": 0.0,
            "action_verified": False,
            "dispensed": False,
            "fp_test_mode": False,
        }

        container = QWidget()
        self.setCentralWidget(container)
        v_lay = QVBoxLayout(container)
        v_lay.setContentsMargins(0, 0, 0, 0)
        v_lay.setSpacing(0)

        self._nav = _NavBar(self._prev, self._next, self._go_first)
        v_lay.addWidget(self._nav)

        self.stack = QStackedWidget()
        v_lay.addWidget(self.stack, stretch=1)

        self.screens = {
            "camera_view":      CameraViewScreen(self),
            "fingerprint_auth": FingerprintAuthScreen(self),
            "auth_result":      AuthResultScreen(self),
            "dispensing":       DispensingScreen(self),
            "medication":       MedicationScreen(self),
            "complete":         CompleteScreen(self),
        }
        for name in _SCREEN_ORDER:
            self.stack.addWidget(self.screens[name])

        self._idx = 0
        self._update_view()

    def show_screen(self, name: str, **kwargs):
        if name in self.screens:
            target_idx = _SCREEN_ORDER.index(name) if name in _SCREEN_ORDER else -1
            if target_idx >= 0:
                self._idx = target_idx
                self._update_view()

    def _update_view(self):
        name = _SCREEN_ORDER[self._idx]
        widget = self.screens[name]

        if name == "auth_result":
            widget.set_result(success=True, user="테스트 사용자")
        elif name == "camera_view":
            widget.set_mode("AUTH")

        self.stack.setCurrentWidget(widget)
        self._nav.set_step(self._idx, len(_SCREEN_ORDER), _SCREEN_LABELS[name])

    def _next(self):
        if self._idx < len(_SCREEN_ORDER) - 1:
            self._idx += 1
            self._update_view()

    def _prev(self):
        if self._idx > 0:
            self._idx -= 1
            self._update_view()

    def _go_first(self):
        self._idx = 0
        self._update_view()


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
