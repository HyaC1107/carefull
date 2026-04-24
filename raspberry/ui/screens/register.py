import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG = "#ede8ff"
_PURPLE = "#7c3aed"
_DARK = "#1e1b4b"
_CARD_BG = "white"


class _StepRow(QWidget):
    def __init__(self, num: int, text: str, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(14)

        badge = QLabel(str(num))
        badge.setFixedSize(28, 28)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFont(QFont("Sans Serif", 13, QFont.Bold))
        badge.setStyleSheet(f"""
            background-color: {_PURPLE};
            color: white;
            border-radius: 14px;
        """)

        label = QLabel(text)
        label.setFont(QFont("Sans Serif", 17))
        label.setStyleSheet(f"color: {_DARK};")

        lay.addWidget(badge)
        lay.addWidget(label)
        lay.addStretch()


class RegisterScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 28)
        root.setSpacing(0)

        # 뒤로가기 버튼
        back_btn = QPushButton("← 메인으로")
        back_btn.setFont(QFont("Sans Serif", 13))
        back_btn.setFixedHeight(36)
        back_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        back_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: 8px;
                padding: 4px 14px;
            }
            QPushButton:pressed { background: #f0f0f0; }
        """)
        back_btn.clicked.connect(lambda: self._go("home"))
        root.addWidget(back_btn, alignment=Qt.AlignLeft)

        root.addStretch(1)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        _icon_path = os.path.join(_ICONS_DIR, "user_register.png")
        if os.path.exists(_icon_path):
            _pix = QPixmap(_icon_path).scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(_pix)
        else:
            icon_lbl.setText("👤")
            icon_lbl.setFont(QFont("Sans Serif", 32))
        root.addWidget(icon_lbl)

        root.addSpacing(10)

        title = QLabel("사용자 등록")
        title.setFont(QFont("Sans Serif", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")
        root.addWidget(title)

        root.addSpacing(20)

        # 등록 절차 카드
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {_CARD_BG};
                border-radius: 16px;
            }}
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(24, 18, 24, 18)
        card_lay.setSpacing(6)

        card_title = QLabel("등록 절차")
        card_title.setFont(QFont("Sans Serif", 16, QFont.Bold))
        card_title.setAlignment(Qt.AlignCenter)
        card_title.setStyleSheet(f"color: {_DARK};")
        card_lay.addWidget(card_title)
        card_lay.addSpacing(8)

        for num, text in [(1, "얼굴 촬영"), (2, "지문 등록"), (3, "저장 완료")]:
            card_lay.addWidget(_StepRow(num, text))

        root.addWidget(card)

        root.addStretch(2)

        # 등록 시작 버튼
        start_btn = QPushButton("등록 시작")
        start_btn.setMinimumHeight(60)
        start_btn.setFont(QFont("Sans Serif", 18, QFont.Bold))
        start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_PURPLE};
                color: white;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:pressed {{ background-color: #6d28d9; }}
        """)
        start_btn.clicked.connect(self._start)
        root.addWidget(start_btn)

    def _start(self):
        if self._app:
            self._app.screens["camera_view"].set_mode("register")
            self._go("camera_view")

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)
