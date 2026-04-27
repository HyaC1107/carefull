import os

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget,
)

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG = "#ede8ff"
_PURPLE = "#7c3aed"
_DARK = "#1e1b4b"

_MOCK_DURATION_MS = 4000   # 실제 R307 연동 전 임시 모의 시간


class _FingerprintWidget(QWidget):
    """지문 아이콘 (동심 호 + 어두운 배경 카드)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self.setFixedSize(160, 160)

    def set_progress(self, pct: int):
        self._progress = max(0, min(100, pct))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        # 어두운 카드 배경
        p.setBrush(QColor("#1e1535"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 20, 20)

        cx, cy = w / 2, h / 2

        # 진행률에 따라 밝기 변화
        base_alpha = 80 + int(self._progress * 1.75)
        color = QColor(_PURPLE)
        color.setAlpha(min(255, base_alpha))

        # 동심 호로 지문 표현
        arcs = [
            (10,  -30 * 16, 240 * 16),
            (17,  -40 * 16, 260 * 16),
            (24,  -50 * 16, 280 * 16),
            (31,  -55 * 16, 290 * 16),
            (38,  -55 * 16, 290 * 16),
            (45,  -50 * 16, 280 * 16),
            (52,  -40 * 16, 250 * 16),
        ]
        for i, (r, start, span) in enumerate(arcs):
            arc_alpha = min(255, 60 + int((self._progress / 100) * 195) + i * 10)
            c = QColor(_PURPLE)
            c.setAlpha(arc_alpha)
            pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                start, span,
            )


class FingerprintRegisterScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._progress = 0
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"FingerprintRegisterScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 24)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        _fp_path = os.path.join(_ICONS_DIR, "fingerprint.png")
        if os.path.exists(_fp_path):
            self._fp_widget = QLabel()
            self._fp_widget.setAlignment(Qt.AlignCenter)
            _pix = QPixmap(_fp_path).scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._fp_widget.setPixmap(_pix)
        else:
            self._fp_widget = _FingerprintWidget()
        root.addWidget(self._fp_widget, alignment=Qt.AlignCenter)
        root.addSpacing(20)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background: #d8b4fe;
            }}
            QProgressBar::chunk {{
                background-color: {_PURPLE};
                border-radius: 4px;
            }}
        """)
        root.addWidget(self._progress_bar)
        root.addSpacing(16)

        self._title_lbl = QLabel("지문을 스캔하는 중...")
        self._title_lbl.setFont(QFont("Sans Serif", 42, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._title_lbl)

        root.addSpacing(8)

        sub = QLabel("센서에 손가락을 올려주세요")
        sub.setFont(QFont("Sans Serif", 30))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_PURPLE};")
        root.addWidget(sub)

        root.addSpacing(8)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(QFont("Sans Serif", 32, QFont.Bold))
        self._pct_lbl.setAlignment(Qt.AlignCenter)
        self._pct_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._pct_lbl)

        root.addStretch(2)

    def showEvent(self, event):
        super().showEvent(event)
        self._progress = 0
        self._progress_bar.setValue(0)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(0)
        self._pct_lbl.setText("0%")
        self._title_lbl.setText("지문을 스캔하는 중...")
        self._start_mock()

    def _start_mock(self):
        # TODO: 실제 R307 스레드로 교체
        step_ms = _MOCK_DURATION_MS // 100
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(step_ms)

    def _tick(self):
        self._progress += 1
        self._progress_bar.setValue(self._progress)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(self._progress)
        self._pct_lbl.setText(f"{self._progress}%")
        if self._progress >= 100:
            self._tick_timer.stop()
            self._title_lbl.setText("등록 완료!")
            QTimer.singleShot(600, self._go_complete)

    def _go_complete(self):
        if self._app:
            self._app.show_screen("register_complete")
