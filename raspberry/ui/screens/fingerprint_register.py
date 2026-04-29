import os

from PyQt5.QtCore import Qt, QThread, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget,
)


class _UploadWorker(QThread):
    def __init__(self, fp_id: int, parent=None):
        super().__init__(parent)
        self._fp_id = fp_id

    def run(self):
        try:
            from api.client import upload_fingerprint
            upload_fingerprint(self._fp_id)
        except Exception as e:
            print(f"[FP UPLOAD ERROR] {e}")

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG = "#ede8ff"
_PURPLE = "#7c3aed"
_DARK = "#1e1b4b"


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
        self._fp_id = None
        self._thread = None
        self._prepare_thread = None
        self._upload_worker = None
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
        self._reset()
        self._prepare_slot()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_thread()

    def _reset(self):
        self._progress = 0
        self._progress_bar.setValue(0)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(0)
        self._pct_lbl.setText("0%")
        self._title_lbl.setText("준비 중...")

    def _prepare_slot(self):
        """서버에서 기존 슬롯 조회 후 다음 빈 슬롯 번호 확정."""
        from ui.threads.fingerprint_thread import FingerprintPrepareThread
        self._prepare_thread = FingerprintPrepareThread(parent=self)
        self._prepare_thread.ready.connect(self._on_slot_ready)
        self._prepare_thread.start()

    def _on_slot_ready(self, next_slot: int):
        self._title_lbl.setText("첫 번째 지문을 올려주세요")
        self._start_enroll(next_slot)

    def _start_enroll(self, position: int = 1):
        self._stop_thread()
        from ui.threads.fingerprint_thread import FingerprintEnrollThread
        self._thread = FingerprintEnrollThread(position=position, parent=self)
        self._thread.stage_changed.connect(self._on_stage)
        self._thread.progress.connect(self._on_progress)
        self._thread.enrolled.connect(self._on_enrolled)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(2000)
        self._thread = None

    def _on_stage(self, msg: str):
        self._title_lbl.setText(msg)

    def _on_progress(self, value: int):
        self._progress_bar.setValue(value)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(value)
        self._pct_lbl.setText(f"{value}%")

    def _on_enrolled(self, fp_id: int):
        self._fp_id = fp_id
        self._title_lbl.setText("등록 완료!")
        self._on_progress(100)
        QTimer.singleShot(600, self._go_complete)

    def _on_failed(self, msg: str):
        self._title_lbl.setText(f"등록 실패: {msg}")

    def _go_complete(self):
        if self._fp_id is not None:
            self._upload_worker = _UploadWorker(self._fp_id, parent=self)
            self._upload_worker.start()
        if self._app:
            self._app.show_screen("register_complete")
