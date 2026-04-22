from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

_BTN_STYLE = """
    QPushButton {{
        background-color: {color};
        color: white;
        border: none;
        border-radius: 14px;
    }}
    QPushButton:pressed {{ background-color: {color}bb; }}
"""


class RegisterScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 50, 40, 50)
        root.setSpacing(0)

        title = QLabel("사용자 등록")
        title.setFont(QFont("Sans Serif", 32, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a2e;")

        desc = QLabel(
            "카메라로 얼굴을 촬영하여\n새 사용자를 등록합니다.\n\n"
            "등록할 분의 이름을 입력한 뒤\n'등록 시작'을 눌러주세요."
        )
        desc.setFont(QFont("Sans Serif", 19))
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #444;")

        name_lbl = QLabel("이름")
        name_lbl.setFont(QFont("Sans Serif", 18))
        name_lbl.setStyleSheet("color: #555;")
        name_lbl.setAlignment(Qt.AlignCenter)

        self._name_input = QLineEdit()
        self._name_input.setFont(QFont("Sans Serif", 22))
        self._name_input.setMinimumHeight(64)
        self._name_input.setAlignment(Qt.AlignCenter)
        self._name_input.setPlaceholderText("예: 홍길동")
        self._name_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #b0c4de;
                border-radius: 12px;
                padding: 8px 16px;
                background: #f9faff;
                color: #1a1a2e;
            }
            QLineEdit:focus { border-color: #4a90d9; }
        """)

        self._warn_lbl = QLabel("")
        self._warn_lbl.setFont(QFont("Sans Serif", 16))
        self._warn_lbl.setAlignment(Qt.AlignCenter)
        self._warn_lbl.setStyleSheet("color: #dc3545;")

        root.addStretch(1)
        root.addWidget(title)
        root.addSpacing(16)
        root.addWidget(desc)
        root.addStretch(2)
        root.addWidget(name_lbl)
        root.addSpacing(8)
        root.addWidget(self._name_input)
        root.addSpacing(6)
        root.addWidget(self._warn_lbl)
        root.addStretch(2)
        root.addWidget(self._make_btn("등록 시작", "#4a90d9", self._start))
        root.addSpacing(14)
        root.addWidget(self._make_btn("취소", "#6c757d", lambda: self._go("home")))

    def _make_btn(self, text: str, color: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(64)
        btn.setFont(QFont("Sans Serif", 22))
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet(_BTN_STYLE.format(color=color))
        btn.clicked.connect(callback)
        return btn

    # ──────────────────────────────── 동작 ───────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._name_input.clear()
        self._warn_lbl.setText("")

    def _start(self):
        name = self._name_input.text().strip()
        if not name:
            self._warn_lbl.setText("이름을 입력해주세요.")
            return
        self._warn_lbl.setText("")
        camera_view = self._app.screens["camera_view"]
        camera_view.set_mode("register", user_name=name)
        self._go("camera_view")

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)
