import json
import os
from datetime import datetime

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

_SCHEDULE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "schedule.json")
)

_BG = "#e8f8f0"
_GREEN = "#16a34a"
_DARK = "#14532d"
_AUTO_HOME_MS = 5000


def _next_medication_time() -> str:
    try:
        with open(_SCHEDULE_PATH, "r", encoding="utf-8") as f:
            schedules = json.load(f)
    except Exception:
        return "--:--"
    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    times = sorted(
        int(e["time"].split(":")[0]) * 60 + int(e["time"].split(":")[1])
        for e in schedules if "time" in e
    )
    if not times:
        return "--:--"
    for t in times:
        if t > now_min:
            h, m = divmod(t, 60)
            return f"{h:02d}:{m:02d}"
    h, m = divmod(times[0], 60)
    return f"{h:02d}:{m:02d}"


class _CheckCircleWidget(QWidget):
    def __init__(self, color: str = _GREEN, size: int = 80, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        r = min(self.width(), self.height()) / 2 - 4
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


class CompleteScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 0, 36, 36)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        root.addWidget(_CheckCircleWidget(), alignment=Qt.AlignCenter)
        root.addSpacing(16)

        title = QLabel("복약 완료")
        title.setFont(QFont("Sans Serif", 26, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")
        root.addWidget(title)

        root.addSpacing(8)

        sub = QLabel("수고하셨습니다")
        sub.setFont(QFont("Sans Serif", 18))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_GREEN};")
        root.addWidget(sub)

        root.addSpacing(20)

        # 다음 복약 카드
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
            }
        """)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(24, 14, 24, 14)
        card_lay.setSpacing(4)

        card_header = QLabel("🕐  다음 복약 시간")
        card_header.setFont(QFont("Sans Serif", 13))
        card_header.setAlignment(Qt.AlignCenter)
        card_header.setStyleSheet(f"color: {_GREEN};")
        card_lay.addWidget(card_header)

        self._next_time_lbl = QLabel("--:--")
        self._next_time_lbl.setFont(QFont("Sans Serif", 28, QFont.Bold))
        self._next_time_lbl.setAlignment(Qt.AlignCenter)
        self._next_time_lbl.setStyleSheet(f"color: {_DARK};")
        card_lay.addWidget(self._next_time_lbl)

        root.addWidget(card)

        root.addSpacing(16)

        self._countdown_lbl = QLabel("")
        self._countdown_lbl.setFont(QFont("Sans Serif", 14))
        self._countdown_lbl.setAlignment(Qt.AlignCenter)
        self._countdown_lbl.setStyleSheet(f"color: {_GREEN};")
        root.addWidget(self._countdown_lbl)

        root.addStretch(2)

    def showEvent(self, event):
        super().showEvent(event)
        self._next_time_lbl.setText(_next_medication_time())
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
        self._countdown_lbl.setText(f"{self._remaining}초 후 메인 화면으로 돌아갑니다")

    def _go_home(self):
        if hasattr(self, "_tick_timer"):
            self._tick_timer.stop()
        if self._app:
            self._app.show_screen("home")
