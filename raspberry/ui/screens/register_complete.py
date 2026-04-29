import os

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG = "#c8f5e2"
_GREEN = "#16a34a"
_DARK = "#14532d"


class _CheckCircleWidget(QWidget):
    def __init__(self, color: str = _GREEN, size: int = 90, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        r = min(w, h) / 2 - 4

        pen = QPen(self._color, 3)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        pen2 = QPen(self._color, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen2)
        s = r * 0.5
        p.drawPolyline(
            QPointF(cx - s * 0.6, cy + s * 0.0),
            QPointF(cx - s * 0.1, cy + s * 0.55),
            QPointF(cx + s * 0.65, cy - s * 0.5),
        )


class RegisterCompleteScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"RegisterCompleteScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 24)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch()

        _check_path = os.path.join(_ICONS_DIR, "check_circle.png")
        if os.path.exists(_check_path):
            check_lbl = QLabel()
            check_lbl.setAlignment(Qt.AlignCenter)
            _pix = QPixmap(_check_path).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            check_lbl.setPixmap(_pix)
            root.addWidget(check_lbl, alignment=Qt.AlignCenter)
        else:
            root.addWidget(_CheckCircleWidget(), alignment=Qt.AlignCenter)

        root.addSpacing(24)

        title = QLabel("등록 완료")
        title.setFont(QFont("Sans Serif", 50, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")
        root.addWidget(title)

        root.addSpacing(10)

        sub = QLabel("메인 화면으로 이동합니다")
        sub.setFont(QFont("Sans Serif", 32))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_GREEN};")
        root.addWidget(sub)

        root.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(2500, self._go_home)

    def _go_home(self):
        if self._app:
            self._app.show_screen("home")
