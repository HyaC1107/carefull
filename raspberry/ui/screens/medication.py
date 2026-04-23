from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.behavior_thread import BehaviorThread, _SUCCESS_FRAMES

_BG = "#e4ecff"
_BLUE = "#3b82f6"
_DARK = "#1e3a8a"
_MANUAL_TIMEOUT_MS = 60_000


class MedicationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._thread = None
        self._timeout_timer = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"background-color: {_BG};")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 24)
        root.setSpacing(0)

        # 카메라 카드 (행위감지 화면 표시)
        self._camera_card = CameraCardWidget(dash_color=_BLUE)
        self._camera_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._camera_card, stretch=3)

        root.addSpacing(18)

        title = QLabel("약을 복용해주세요")
        title.setFont(QFont("Sans Serif", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")
        root.addWidget(title)

        root.addSpacing(6)

        self._sub_lbl = QLabel("물과 함께 드세요")
        self._sub_lbl.setFont(QFont("Sans Serif", 15))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet(f"color: {_BLUE};")
        root.addWidget(self._sub_lbl)

        root.addStretch(1)

    def showEvent(self, event):
        super().showEvent(event)
        self._sub_lbl.setText("물과 함께 드세요")
        self._start_thread()
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_intake)
        self._timeout_timer.start(_MANUAL_TIMEOUT_MS)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_thread()
        if self._timeout_timer:
            self._timeout_timer.stop()

    def _start_thread(self):
        self._stop_thread()
        self._thread = BehaviorThread(parent=self)
        self._thread.progress_updated.connect(self._on_progress)
        self._thread.intake_detected.connect(self._on_intake)
        self._thread.start()

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(3000)
        self._thread = None

    def _on_progress(self, current: int, required: int):
        pct = int(current / required * 100)
        self._sub_lbl.setText(f"복약 감지 중... {pct}%")

    def _on_intake(self):
        self._stop_thread()
        if self._timeout_timer:
            self._timeout_timer.stop()
        if self._app:
            self._app.show_screen("complete")
