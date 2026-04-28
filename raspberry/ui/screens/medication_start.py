from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QLabel,
)

_BG = "#fff8e8"
_ORANGE = "#f97316"
_TEXT = "#7c4a1a"


class _BellWidget(QWidget):
    """알림 벨 아이콘 (주황 벨 + 분홍 도트)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2

        pen = QPen(QColor(_ORANGE), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        # 벨 몸통 (둥근 사다리꼴 느낌)
        body = QPainterPath()
        body.moveTo(cx, cy - 30)
        body.cubicTo(cx + 24, cy - 30, cx + 28, cy - 10, cx + 28, cy + 8)
        body.lineTo(cx - 28, cy + 8)
        body.cubicTo(cx - 28, cy - 10, cx - 24, cy - 30, cx, cy - 30)
        p.drawPath(body)

        # 벨 손잡이 (상단 반원)
        p.drawArc(int(cx - 8), int(cy - 36), 16, 14, 0, 180 * 16)

        # 벨 하단 (clapper)
        p.drawArc(int(cx - 10), int(cy + 6), 20, 12, 180 * 16, 180 * 16)

        # 분홍 알림 도트
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#fb7185"))
        p.drawEllipse(QRectF(cx + 16, cy - 32, 14, 14))


class MedicationStartScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._auto_timer = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"MedicationStartScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 0, 32, 24)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        bell = _BellWidget()
        root.addWidget(bell, alignment=Qt.AlignCenter)
        root.addSpacing(24)

        title = QLabel("약 드실 시간입니다")
        title.setFont(QFont("Sans Serif", 48, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_TEXT};")
        root.addWidget(title)

        root.addSpacing(10)

        sub = QLabel("잠시 후 얼굴 인증을 시작합니다")
        sub.setFont(QFont("Sans Serif", 30))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_ORANGE};")
        root.addWidget(sub)

        root.addStretch(2)

        start_btn = QPushButton("복약 프로세스 시작")
        start_btn.setMinimumHeight(60)
        start_btn.setFont(QFont("Sans Serif", 28, QFont.Bold))
        start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_ORANGE};
                color: white;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:pressed {{ background-color: #ea6c0a; }}
        """)
        start_btn.clicked.connect(self._go_auth)
        root.addWidget(start_btn)

    def showEvent(self, event):
        super().showEvent(event)
        self._auto_timer = QTimer.singleShot(5000, self._go_auth)

    def _go_auth(self):
        if self._app:
            self._app.screens["camera_view"].set_mode("auth")
            self._app.show_screen("camera_view")
