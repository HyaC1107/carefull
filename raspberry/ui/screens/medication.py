from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt5.QtWidgets import QLabel, QPushButton, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.behavior_thread import BehaviorThread

_MANUAL_TIMEOUT_MS = 60_000


class _GradientOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 180))
        p.fillRect(self.rect(), grad)


class MedicationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._thread = None
        self._timeout_timer = None
        self._build_ui()

    def _build_ui(self):
        self._camera_card = CameraCardWidget(dash_color="#3b82f6", parent=self)

        self._gradient = _GradientOverlay(parent=self)

        # 중단 버튼 추가
        self._btn_cancel = QPushButton("중단", parent=self)
        self._btn_cancel.setFont(QFont("Sans Serif", 20, QFont.Bold))
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 180);
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: 12px;
                padding: 8px;
            }
            QPushButton:pressed { background: white; }
        """)
        self._btn_cancel.clicked.connect(self._on_cancel)

        self._title_lbl = QLabel("약을 복용해주세요", parent=self)
        self._title_lbl.setFont(QFont("Sans Serif", 42, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet("color: #ffffff; background: transparent;")
        self._title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._sub_lbl = QLabel("물과 함께 드세요", parent=self)
        self._sub_lbl.setFont(QFont("Sans Serif", 34))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet("color: #93c5fd; background: transparent;")
        self._sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._camera_card.setGeometry(0, 0, w, h)

        # 우측 상단 중단 버튼 배치
        self._btn_cancel.setGeometry(w - 140, 25, 120, 60)

        overlay_h = int(h * 0.32)
        self._gradient.setGeometry(0, h - overlay_h, w, overlay_h)
        self._title_lbl.setGeometry(0, h - int(h * 0.22), w, 64)
        self._sub_lbl.setGeometry(0, h - int(h * 0.12), w, 52)

    def showEvent(self, event):
        super().showEvent(event)
        self._sub_lbl.setText("물과 함께 드세요")
        self._sub_lbl.setStyleSheet("color: #93c5fd; background: transparent;")
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
        self._thread.frame_ready.connect(self._camera_card.update_frame)
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

    def _on_cancel(self):
        self._stop_thread()
        if self._timeout_timer:
            self._timeout_timer.stop()
        if self._app:
            self._app.show_screen("home")

    def _on_intake(self):
        self._stop_thread()
        if self._timeout_timer:
            self._timeout_timer.stop()
        if self._app:
            self._app.current_session["action_verified"] = True
            self._app.show_screen("complete")
