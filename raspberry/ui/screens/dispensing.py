from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget

from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

def _play_voice(filename: str):
    try:
        from hardware.alarm import play_voice
        play_voice(filename)
    except Exception:
        pass


_BG = "#dde3f8"
_INDIGO = "#4338ca"
_DARK = "#1e1b5e"
_TRANSITION_MS = 3500


class _DispenseThread(QThread):
    done = pyqtSignal()

    def run(self):
        try:
            from hardware.motor import dispense_medicine
            dispense_medicine()
        except Exception as e:
            print(f"[DISPENSE ERROR] {e}")
        self.done.emit()


class _PillsWidget(QWidget):
    """약 캡슐 3개 아이콘 (QPainter 드로잉)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(176, 76)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(_INDIGO), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        configs = [
            (25, 38, -30),
            (88, 33, 0),
            (151, 38, 30),
        ]
        for cx, cy, angle in configs:
            p.save()
            p.translate(cx, cy)
            p.rotate(angle)
            pw, ph = 33, 15
            p.drawRoundedRect(-pw // 2, -ph // 2, pw, ph, ph // 2, ph // 2)
            p.drawLine(0, -ph // 2, 0, ph // 2)
            p.restore()


class DispensingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"DispensingScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 0, 32, 24)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        root.addWidget(_PillsWidget(), alignment=Qt.AlignCenter)
        root.addSpacing(20)

        title = QLabel("약이 나옵니다")
        title.setFont(QFont("Sans Serif", _fs(56), QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")
        root.addWidget(title)

        root.addSpacing(16)

        # ── 진행바 (가로 폭 절반으로 축소) ──
        prog_row = QHBoxLayout()
        prog_row.addStretch()
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setFixedWidth(400) # 가로 폭 고정값으로 제한
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background: #c7d2fe;
            }}
            QProgressBar::chunk {{
                background-color: {_INDIGO};
                border-radius: 4px;
            }}
        """)
        prog_row.addWidget(self._progress_bar)
        prog_row.addStretch()
        root.addLayout(prog_row)

        root.addSpacing(14)

        sub = QLabel("잠시만 기다려주세요")
        sub.setFont(QFont("Sans Serif", _fs(36)))
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"color: {_INDIGO};")
        root.addWidget(sub)

        root.addStretch(2)

    def showEvent(self, event):
        super().showEvent(event)
        _play_voice("med_dispensing.mp3")
        self._progress_bar.setValue(0)
        self._start_progress()
        self._start_dispense()

    def _start_progress(self):
        self._progress_val = 0
        step_ms = _TRANSITION_MS // 100
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._tick_progress)
        self._progress_timer.start(step_ms)

    def _tick_progress(self):
        self._progress_val += 1
        self._progress_bar.setValue(self._progress_val)
        if self._progress_val >= 100:
            self._progress_timer.stop()

    def _start_dispense(self):
        if self._thread and self._thread.isRunning():
            return
        self._thread = _DispenseThread(parent=self)
        self._thread.done.connect(self._on_dispense_done)
        self._thread.start()

    def _on_dispense_done(self):
        if self._app:
            self._app.current_session["dispensed"] = True
        QTimer.singleShot(_TRANSITION_MS, self._go_medication)

    def _go_medication(self):
        if self._app:
            self._app.show_screen("medication")
