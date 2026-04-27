import os

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_AUTO_SUCCESS_MS = 2000
_AUTO_FAIL_MS = 3000


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
        self._build_ui()

    def set_result(self, success: bool, user: str = None, fingerprint: bool = False):
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
            QTimer.singleShot(_AUTO_SUCCESS_MS, lambda: self._go("dispensing"))
        else:
            self.setStyleSheet("AuthResultScreen { background-color: #ffeaea; }")
            self._card.set_state(_ResultCardWidget.FAIL)
            self._card.show()
            self._icon_lbl.hide()
            self._title_lbl.setText("인증 실패")
            self._title_lbl.setStyleSheet("color: #7f1d1d;")
            self._sub_lbl.setText("다시 시도해주세요")
            self._sub_lbl.setStyleSheet("color: #ef4444;")
            QTimer.singleShot(_AUTO_FAIL_MS, lambda: self._go("home"))

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
        self._title_lbl.setFont(QFont("Sans Serif", 26, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._title_lbl)

        root.addSpacing(6)

        self._sub_lbl = QLabel("약을 준비하고 있습니다")
        self._sub_lbl.setFont(QFont("Sans Serif", 16))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._sub_lbl)

        root.addStretch(1)

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)
