from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

_AUTO_SUCCESS_MS = 2000
_AUTO_FAIL_MS = 3000


class AuthResultScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._timer = None
        self._build_ui()

    def set_result(self, success: bool, user: str = None):
        self._cancel_timer()

        if success:
            self._icon_lbl.setText("✓")
            self._icon_lbl.setStyleSheet("color: #28a745; font-size: 100px;")
            name = user or "사용자"
            self._msg_lbl.setText(f"인증 성공\n{name}님, 안녕하세요!")
            self._msg_lbl.setStyleSheet("color: #28a745;")
            self._sub_lbl.setText("약을 배출합니다...")
            self._timer = QTimer.singleShot(
                _AUTO_SUCCESS_MS, lambda: self._go("dispensing")
            )
        else:
            self._icon_lbl.setText("✗")
            self._icon_lbl.setStyleSheet("color: #dc3545; font-size: 100px;")
            self._msg_lbl.setText("인증 실패\n다시 시도해주세요")
            self._msg_lbl.setStyleSheet("color: #dc3545;")
            self._sub_lbl.setText("홈으로 돌아갑니다...")
            self._timer = QTimer.singleShot(
                _AUTO_FAIL_MS, lambda: self._go("home")
            )

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 60, 40, 60)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        self._icon_lbl = QLabel()
        self._icon_lbl.setFont(QFont("Sans Serif", 80, QFont.Bold))
        self._icon_lbl.setAlignment(Qt.AlignCenter)

        self._msg_lbl = QLabel()
        self._msg_lbl.setFont(QFont("Sans Serif", 28, QFont.Bold))
        self._msg_lbl.setAlignment(Qt.AlignCenter)
        self._msg_lbl.setWordWrap(True)

        self._sub_lbl = QLabel()
        self._sub_lbl.setFont(QFont("Sans Serif", 18))
        self._sub_lbl.setStyleSheet("color: #888;")
        self._sub_lbl.setAlignment(Qt.AlignCenter)

        root.addStretch()
        root.addWidget(self._icon_lbl)
        root.addSpacing(24)
        root.addWidget(self._msg_lbl)
        root.addSpacing(12)
        root.addWidget(self._sub_lbl)
        root.addStretch()

    # ──────────────────────────────── 헬퍼 ───────────────────────────────────

    def _cancel_timer(self):
        # QTimer.singleShot returns None; store nothing. Just guard re-entry.
        self._timer = None

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)
