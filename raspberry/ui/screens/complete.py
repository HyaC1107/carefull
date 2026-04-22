from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

_AUTO_HOME_MS = 5000


class CompleteScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 60, 40, 60)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        icon = QLabel("✅")
        icon.setFont(QFont("Sans Serif", 80))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("복약 완료!")
        title.setFont(QFont("Sans Serif", 36, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #28a745;")

        msg = QLabel("오늘도 건강하게 복약하셨습니다.\n수고하셨습니다!")
        msg.setFont(QFont("Sans Serif", 22))
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #444;")

        self._countdown_lbl = QLabel("")
        self._countdown_lbl.setFont(QFont("Sans Serif", 17))
        self._countdown_lbl.setAlignment(Qt.AlignCenter)
        self._countdown_lbl.setStyleSheet("color: #999;")

        home_btn = QPushButton("홈으로")
        home_btn.setMinimumHeight(64)
        home_btn.setFont(QFont("Sans Serif", 22))
        home_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 14px;
            }
            QPushButton:pressed { background-color: #3a7bc8; }
        """)
        home_btn.clicked.connect(self._go_home)

        root.addStretch()
        root.addWidget(icon)
        root.addSpacing(20)
        root.addWidget(title)
        root.addSpacing(14)
        root.addWidget(msg)
        root.addSpacing(20)
        root.addWidget(self._countdown_lbl)
        root.addStretch()
        root.addWidget(home_btn)

    # ──────────────────────────────── 생명주기 ────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._remaining = _AUTO_HOME_MS // 1000
        self._update_countdown()
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_tick_timer"):
            self._tick_timer.stop()

    def _tick(self):
        self._remaining -= 1
        self._update_countdown()
        if self._remaining <= 0:
            self._tick_timer.stop()
            self._go_home()

    def _update_countdown(self):
        self._countdown_lbl.setText(f"{self._remaining}초 후 홈으로 돌아갑니다")

    def _go_home(self):
        if hasattr(self, "_tick_timer"):
            self._tick_timer.stop()
        if self._app:
            self._app.show_screen("home")
