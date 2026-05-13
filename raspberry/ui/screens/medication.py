from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.behavior_thread import BehaviorThread
from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

def _play_voice(filename: str):
    try:
        from hardware.alarm import play_voice
        play_voice(filename)
    except Exception:
        pass


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

        self._btn_cancel = QPushButton("중단", parent=self)
        self._btn_cancel.setFont(QFont("Sans Serif", _fs(26), QFont.Bold))
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
        self._title_lbl.setFont(QFont("Sans Serif", _fs(52), QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet("color: #ffffff; background: transparent;")
        self._title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._sub_lbl = QLabel("물과 함께 드세요", parent=self)
        self._sub_lbl.setFont(QFont("Sans Serif", _fs(42)))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet("color: #93c5fd; background: transparent;")
        self._sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        # ── 수동 확인 팝업 (타임아웃 시 표시) ─────────────────────────────
        self._confirm_overlay = QWidget(parent=self)
        self._confirm_overlay.setStyleSheet("background-color: rgba(15, 23, 42, 220);")
        self._confirm_overlay.hide()

        overlay_lay = QVBoxLayout(self._confirm_overlay)
        overlay_lay.setAlignment(Qt.AlignCenter)
        overlay_lay.setSpacing(_fs(24))

        _q_lbl = QLabel("복약하셨나요?", self._confirm_overlay)
        _q_lbl.setFont(QFont("Sans Serif", _fs(54), QFont.Bold))
        _q_lbl.setAlignment(Qt.AlignCenter)
        _q_lbl.setStyleSheet("color: white;")
        overlay_lay.addWidget(_q_lbl)

        _sub_confirm = QLabel("AI가 확인하지 못했습니다\n직접 선택해주세요", self._confirm_overlay)
        _sub_confirm.setFont(QFont("Sans Serif", _fs(32)))
        _sub_confirm.setAlignment(Qt.AlignCenter)
        _sub_confirm.setStyleSheet("color: #94a3b8;")
        overlay_lay.addWidget(_sub_confirm)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(_fs(24))
        btn_row.setAlignment(Qt.AlignCenter)

        self._btn_yes = QPushButton("네, 복약했습니다", self._confirm_overlay)
        self._btn_yes.setFont(QFont("Sans Serif", _fs(30), QFont.Bold))
        self._btn_yes.setFixedHeight(_fs(90))
        self._btn_yes.setFixedWidth(_fs(380))
        self._btn_yes.setStyleSheet("""
            QPushButton { background-color: #22c55e; color: white; border-radius: 16px; border: none; }
            QPushButton:pressed { background-color: #16a34a; }
        """)
        self._btn_yes.clicked.connect(self._on_confirm_yes)

        self._btn_no = QPushButton("아니요", self._confirm_overlay)
        self._btn_no.setFont(QFont("Sans Serif", _fs(30), QFont.Bold))
        self._btn_no.setFixedHeight(_fs(90))
        self._btn_no.setFixedWidth(_fs(240))
        self._btn_no.setStyleSheet("""
            QPushButton { background-color: transparent; color: white; border-radius: 16px; border: 2px solid white; }
            QPushButton:pressed { background-color: rgba(255,255,255,30); }
        """)
        self._btn_no.clicked.connect(self._on_confirm_no)

        btn_row.addWidget(self._btn_yes)
        btn_row.addWidget(self._btn_no)
        overlay_lay.addLayout(btn_row)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._camera_card.setGeometry(0, 0, w, h)

        btn_w, btn_h = _fs(140), _fs(60)
        self._btn_cancel.setGeometry(w - btn_w - _fs(20), _fs(20), btn_w, btn_h)

        title_h = QFontMetrics(self._title_lbl.font()).height() + _fs(16)
        sub_h   = QFontMetrics(self._sub_lbl.font()).height() + _fs(14)
        pad_bot = _fs(24)
        sub_y   = h - pad_bot - sub_h
        title_y = sub_y - _fs(12) - title_h

        gradient_top = max(0, title_y - _fs(24))
        self._gradient.setGeometry(0, gradient_top, w, h - gradient_top)
        self._title_lbl.setGeometry(0, title_y, w, title_h)
        self._sub_lbl.setGeometry(0, sub_y, w, sub_h)
        self._confirm_overlay.setGeometry(0, 0, w, h)

    def showEvent(self, event):
        super().showEvent(event)
        self._confirm_overlay.hide()
        _play_voice("med_take.mp3")
        self._sub_lbl.setText("물과 함께 드세요")
        self._sub_lbl.setStyleSheet("color: #93c5fd; background: transparent;")
        self._start_thread()
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)
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
        """BehaviorThread 가 복약 동작 감지 → AI 검증 성공."""
        self._stop_thread()
        if self._timeout_timer:
            self._timeout_timer.stop()
        if self._app:
            self._app.current_session["action_verified"] = True
            self._app.show_screen("complete")

    def _on_timeout(self):
        """60초 타임아웃 — AI 미감지, 수동 확인 팝업 표시."""
        self._stop_thread()
        self._confirm_overlay.show()

    def _on_confirm_yes(self):
        """사용자가 '네, 복약했습니다' 선택 — action_verified=False로 기록 (AI 미검증)."""
        self._confirm_overlay.hide()
        if self._app:
            self._app.current_session["action_verified"] = False
            self._app.show_screen("complete")

    def _on_confirm_no(self):
        """사용자가 '아니요' 선택 — 복약 안 함, 홈으로 복귀."""
        self._confirm_overlay.hide()
        if self._app:
            self._app.current_session["action_verified"] = False
            self._app.show_screen("home")
