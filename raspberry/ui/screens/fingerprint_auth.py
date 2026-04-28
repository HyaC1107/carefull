import os

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QLabel, QProgressBar, QVBoxLayout, QWidget,
)

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG = "#e8f0fe"
_BLUE = "#3b82f6"
_DARK = "#1e3a5f"

_AUTH_TIMEOUT_MS = 30_000


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

        p.setBrush(QColor("#0f1e3a"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 20, 20)

        cx, cy = w / 2, h / 2

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
            c = QColor(_BLUE)
            c.setAlpha(arc_alpha)
            pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                start, span,
            )


class FingerprintAuthScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._progress = 0
        self._thread = None
        self._timeout_timer = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"FingerprintAuthScreen {{ background-color: {_BG}; }}")
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
                background: #bfdbfe;
            }}
            QProgressBar::chunk {{
                background-color: {_BLUE};
                border-radius: 4px;
            }}
        """)
        root.addWidget(self._progress_bar)
        root.addSpacing(16)

        self._title_lbl = QLabel("지문을 인증하는 중...")
        self._title_lbl.setFont(QFont("Sans Serif", 42, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._title_lbl)

        root.addSpacing(8)

        sub = QLabel("센서에 손가락을 올려주세요")
        sub.setFont(QFont("Sans Serif", 30))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_BLUE};")
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
        self._reset()
        self._start_auth()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_timers()

    def _reset(self):
        self._progress = 0
        self._progress_bar.setValue(0)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(0)
        self._pct_lbl.setText("0%")
        self._title_lbl.setText("센서에 손가락을 올려주세요")

    def _start_auth(self):
        self._stop_thread()

        from ui.threads.fingerprint_thread import FingerprintSearchThread
        self._thread = FingerprintSearchThread(parent=self)
        self._thread.found.connect(self._on_found)
        self._thread.not_found.connect(self._on_not_found)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_auth_failure)
        self._timeout_timer.start(_AUTH_TIMEOUT_MS)

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(2000)
        self._thread = None

    def _stop_timers(self):
        if self._timeout_timer and self._timeout_timer.isActive():
            self._timeout_timer.stop()
        self._stop_thread()

    def _on_found(self, position: int, score: int):
        self._stop_timers()
        self._title_lbl.setText("인증 완료!")
        self._progress_bar.setValue(100)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(100)
        self._pct_lbl.setText("100%")
        QTimer.singleShot(400, self._on_auth_success)

    def _on_not_found(self):
        self._stop_timers()
        self._title_lbl.setText("등록되지 않은 지문입니다")
        QTimer.singleShot(1500, self._on_auth_failure)

    def _on_failed(self, msg: str):
        self._stop_timers()
        self._title_lbl.setText(f"오류: {msg}")
        QTimer.singleShot(1500, self._on_auth_failure)

    def _on_auth_success(self):
        if not self._app:
            return
        if self._app.current_session.get("fp_test_mode"):
            self._app.current_session["fp_test_mode"] = False
            self._app.show_screen("home")
            return
        # 얼굴 인증 없이 지문으로 통과 — face_verified는 False 유지
        result = self._app.screens["auth_result"]
        result.set_result(success=True, fingerprint=True)
        self._app.show_screen("auth_result")

    def _on_auth_failure(self):
        self._stop_timers()
        if not self._app:
            return
        if self._app.current_session.get("fp_test_mode"):
            self._app.current_session["fp_test_mode"] = False
            self._app.show_screen("home")
            return
        result = self._app.screens["auth_result"]
        result.set_result(success=False)
        self._app.show_screen("auth_result")
