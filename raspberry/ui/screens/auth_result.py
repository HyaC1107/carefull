import copy
import os

from PyQt5.QtCore import QPointF, QRectF, Qt, QThread, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

def _play_voice(filename: str):
    try:
        from hardware.alarm import play_voice
        play_voice(filename)
    except Exception:
        pass


_AUTO_SUCCESS_MS = 3500
_AUTO_FAIL_MS = 4000


class _FailEventSendWorker(QThread):
    """인증 실패 로그를 백그라운드에서 서버로 전송."""
    def __init__(self, session: dict, parent=None):
        super().__init__(parent)
        self._session = session

    def run(self):
        sche_id = self._session.get("sche_id")
        if sche_id is None:
            return
        from api.client import send_device_event
        send_device_event(
            sche_id=sche_id,
            face_verified=self._session.get("face_verified", False),
            dispensed=False,
            action_verified=False,
            raw_confidence=self._session.get("similarity_score", 0.0),
            error_code="AUTH_FAILED",
        )


class _ResultCardWidget(QWidget):
    """인증 결과를 카메라 카드 크기/위치로 표시하는 위젯."""

    SUCCESS = "success"
    FAIL = "fail"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self.SUCCESS
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_state(self, state: str):
        self._state = state
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        if self._state == self.SUCCESS:
            card_color = QColor("#1a3540")
            icon_color = QColor("#22c55e")
        else:
            card_color = QColor("#3a1a1a")
            icon_color = QColor("#ef4444")

        # 카드 배경
        p.setBrush(card_color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 16, 16)

        cx, cy = w / 2, h / 2
        r = min(w, h) * 0.22

        # 원 테두리
        pen = QPen(icon_color, 3)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # 체크 or X
        pen2 = QPen(icon_color, 5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen2)

        if self._state == self.SUCCESS:
            s = r * 0.52
            p.drawPolyline(
                QPointF(cx - s * 0.6, cy + s * 0.0),
                QPointF(cx - s * 0.1, cy + s * 0.55),
                QPointF(cx + s * 0.65, cy - s * 0.5),
            )
        else:
            s = r * 0.42
            p.drawLine(QPointF(cx - s, cy - s), QPointF(cx + s, cy + s))
            p.drawLine(QPointF(cx + s, cy - s), QPointF(cx - s, cy + s))


class AuthResultScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._pending_timer = None
        self._fail_worker = None
        self._build_ui()

    def _cancel_pending(self):
        if self._pending_timer is not None:
            self._pending_timer.stop()
            self._pending_timer = None

    def hideEvent(self, event):
        super().hideEvent(event)
        self._cancel_pending()

    def set_result(self, success: bool, user: str = None, fingerprint: bool = False):
        self._cancel_pending()   # 이전 결과의 타이머가 남아 있으면 취소
        _play_voice("med_auth_success.mp3" if success else "med_auth_fail.mp3")
        if success:
            self.setStyleSheet("AuthResultScreen { background-color: #dff4ef; }")
            _png = os.path.join(_ICONS_DIR, "check_small.png")
            if os.path.exists(_png):
                _pix = QPixmap(_png).scaled(190, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._icon_lbl.setPixmap(_pix)
                self._icon_lbl.show()
                self._card.hide()
            else:
                self._card.set_state(_ResultCardWidget.SUCCESS)
                self._card.show()
                self._icon_lbl.hide()
            self._title_lbl.setText("인증 완료")
            self._title_lbl.setStyleSheet("color: #1e3a5f;")
            sub = "지문으로 확인되었습니다" if fingerprint else "약을 준비하고 있습니다"
            self._sub_lbl.setText(sub)
            self._sub_lbl.setStyleSheet("color: #3b82f6;")
            self._pending_timer = QTimer(self)
            self._pending_timer.setSingleShot(True)
            self._pending_timer.timeout.connect(lambda: self._go("dispensing"))
            self._pending_timer.start(_AUTO_SUCCESS_MS)
        else:
            self.setStyleSheet("AuthResultScreen { background-color: #ffeaea; }")
            self._card.set_state(_ResultCardWidget.FAIL)
            self._card.show()
            self._icon_lbl.hide()
            self._title_lbl.setText("인증 실패")
            self._title_lbl.setStyleSheet("color: #7f1d1d;")
            self._sub_lbl.setText("다시 시도해주세요")
            self._sub_lbl.setStyleSheet("color: #ef4444;")
            if self._app:
                session = copy.copy(self._app.current_session)
                self._fail_worker = _FailEventSendWorker(session, parent=self)
                self._fail_worker.start()
            self._pending_timer = QTimer(self)
            self._pending_timer.setSingleShot(True)
            self._pending_timer.timeout.connect(lambda: self._go("home"))
            self._pending_timer.start(_AUTO_FAIL_MS)

    def _build_ui(self):
        self.setStyleSheet("AuthResultScreen { background-color: #dff4ef; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 24)
        root.setSpacing(0)

        self._card = _ResultCardWidget()
        self._card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._icon_lbl = QLabel()
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        root.addWidget(self._card, stretch=3)
        root.addWidget(self._icon_lbl, stretch=3)
        self._icon_lbl.hide()

        root.addSpacing(18)

        self._title_lbl = QLabel("인증 완료")
        self._title_lbl.setFont(QFont("Sans Serif", _fs(52), QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._title_lbl)

        root.addSpacing(6)

        self._sub_lbl = QLabel("약을 준비하고 있습니다")
        self._sub_lbl.setFont(QFont("Sans Serif", _fs(36)))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._sub_lbl)

        root.addStretch(1)

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)
