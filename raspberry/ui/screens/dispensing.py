from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

_TRANSITION_MS = 3500   # 모터 동작 후 medication 화면 전환 대기


class _DispenseThread(QThread):
    done = pyqtSignal()

    def __init__(self, user: str = "user", parent=None):
        super().__init__(parent)
        self._user = user

    def run(self):
        try:
            from hardware.dispenser import dispense_medicine
            dispense_medicine(self._user)
        except Exception as e:
            print(f"[DISPENSE ERROR] {e}")
        self.done.emit()


class DispensingScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._thread = None
        self._dot_step = 0
        self._build_ui()
        self._init_dot_timer()

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 60, 40, 60)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        icon = QLabel("💊")
        icon.setFont(QFont("Sans Serif", 72))
        icon.setAlignment(Qt.AlignCenter)

        msg = QLabel("약을 배출하고 있습니다\n잠시만 기다려주세요")
        msg.setFont(QFont("Sans Serif", 26, QFont.Bold))
        msg.setAlignment(Qt.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #1a1a2e;")

        self._dot_lbl = QLabel("●")
        self._dot_lbl.setFont(QFont("Sans Serif", 36))
        self._dot_lbl.setStyleSheet("color: #4a90d9;")
        self._dot_lbl.setAlignment(Qt.AlignCenter)

        root.addStretch()
        root.addWidget(icon)
        root.addSpacing(24)
        root.addWidget(msg)
        root.addSpacing(32)
        root.addWidget(self._dot_lbl)
        root.addStretch()

    def _init_dot_timer(self):
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dot)
        self._dot_timer.start(400)

    def _animate_dot(self):
        dots = ["●　　", "●●　", "●●●"]
        self._dot_lbl.setText(dots[self._dot_step % 3])
        self._dot_step += 1

    # ──────────────────────────────── 생명주기 ────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._dot_step = 0
        self._start_dispense()

    def _start_dispense(self):
        if self._thread and self._thread.isRunning():
            return
        self._thread = _DispenseThread(parent=self)
        self._thread.done.connect(
            lambda: QTimer.singleShot(_TRANSITION_MS, self._go_medication)
        )
        self._thread.start()

    def _go_medication(self):
        if self._app:
            self._app.show_screen("medication")
