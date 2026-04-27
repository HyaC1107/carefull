import os
import socket
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QScroller, QSizePolicy, QSlider, QVBoxLayout, QWidget,
)

_BG = "#f5f6fa"
_CARD = "white"
_DARK = "#1e293b"
_GRAY = "#64748b"
_GREEN = "#16a34a"
_BLUE = "#3b82f6"
_ORANGE = "#f97316"

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_ICON_SIZE = 52
_CARD_PAD_H = 28
_CARD_PAD_V = 22


def _icon_label(png_name: str, fallback: str, size: int = _ICON_SIZE) -> QLabel:
    lbl = QLabel()
    lbl.setStyleSheet("background: transparent; border: none;")
    path = os.path.join(_ICONS_DIR, png_name)
    if os.path.exists(path):
        pix = QPixmap(path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl.setPixmap(pix)
        lbl.setFixedSize(size, size)
    else:
        lbl.setText(fallback)
        lbl.setFont(QFont("Sans Serif", 22))
    return lbl


def _check_network() -> bool:
    try:
        socket.setdefaulttimeout(1)
        socket.gethostbyname("8.8.8.8")
        return True
    except Exception:
        return False


class _StatusCard(QFrame):
    def __init__(self, png_name: str, fallback_icon: str, title: str, subtitle: str, ok: bool, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        lay.setSpacing(20)

        lay.addWidget(_icon_label(png_name, fallback_icon))

        text_lay = QVBoxLayout()
        text_lay.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont("Sans Serif", 22, QFont.Bold))
        t.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        text_lay.addWidget(t)

        s = QLabel(subtitle)
        s.setFont(QFont("Sans Serif", 18))
        s.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        text_lay.addWidget(s)

        lay.addLayout(text_lay)
        lay.addStretch()

        badge = QLabel("정상" if ok else "오류")
        badge.setFont(QFont("Sans Serif", 18, QFont.Bold))
        badge_color = "#dcfce7" if ok else "#fee2e2"
        badge_text = _GREEN if ok else "#dc2626"
        badge.setStyleSheet(f"""
            background-color: {badge_color};
            color: {badge_text};
            border-radius: 10px;
            padding: 6px 18px;
        """)
        lay.addWidget(badge)


class _VolumeCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        lay.setSpacing(14)

        top = QHBoxLayout()
        top.addWidget(_icon_label("volume.png", "♪"))
        top.addSpacing(16)

        title_lbl = QLabel("알림 음량")
        title_lbl.setFont(QFont("Sans Serif", 22, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")

        self._pct_lbl = QLabel("70%")
        self._pct_lbl.setFont(QFont("Sans Serif", 22, QFont.Bold))
        self._pct_lbl.setStyleSheet(f"color: {_BLUE}; background: transparent; border: none;")

        top.addWidget(title_lbl)
        top.addStretch()
        top.addWidget(self._pct_lbl)
        lay.addLayout(top)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(70)
        self._slider.setFixedHeight(40)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                width: 28px;
                height: 28px;
                margin: -10px 0;
                background: {_BLUE};
                border-radius: 14px;
            }}
            QSlider::sub-page:horizontal {{
                background: {_BLUE};
                border-radius: 4px;
            }}
        """)
        self._slider.valueChanged.connect(lambda v: self._pct_lbl.setText(f"{v}%"))
        lay.addWidget(self._slider)


class _ControlCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        lay.setSpacing(14)

        top = QHBoxLayout()
        top.addWidget(_icon_label("control.png", "⚙"))
        top.addSpacing(16)

        title_lbl = QLabel("기기 제어")
        title_lbl.setFont(QFont("Sans Serif", 22, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        top.addWidget(title_lbl)
        top.addStretch()
        lay.addLayout(top)

        restart_btn = QPushButton("재시작")
        restart_btn.setMinimumHeight(60)
        restart_btn.setFont(QFont("Sans Serif", 22))
        restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fff3e0;
                color: {_ORANGE};
                border: 2px solid #fed7aa;
                border-radius: 12px;
            }}
            QPushButton:pressed {{ background-color: #ffe0b2; }}
        """)
        restart_btn.clicked.connect(self._restart)
        lay.addWidget(restart_btn)

        exit_btn = QPushButton("앱 종료")
        exit_btn.setMinimumHeight(60)
        exit_btn.setFont(QFont("Sans Serif", 22))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #dc2626;
                border: 2px solid #fca5a5;
                border-radius: 12px;
            }
            QPushButton:pressed { background-color: #fecaca; }
        """)
        exit_btn.clicked.connect(QApplication.quit)
        lay.addWidget(exit_btn)

    @staticmethod
    def _restart():
        try:
            os.system("sudo reboot")
        except Exception:
            pass


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"SettingsScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(0)

        # 상단 헤더
        header = QHBoxLayout()
        back_btn = QPushButton("← 메인으로")
        back_btn.setFont(QFont("Sans Serif", 18))
        back_btn.setFixedHeight(48)
        back_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        back_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: 10px;
                padding: 4px 18px;
            }
            QPushButton:pressed { background: #f0f0f0; }
        """)
        back_btn.clicked.connect(lambda: self._app.show_screen("home"))

        title = QLabel("설정")
        title.setFont(QFont("Sans Serif", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")

        spacer = QWidget()
        spacer.setFixedWidth(back_btn.sizeHint().width())

        header.addWidget(back_btn)
        header.addStretch()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(spacer)
        root.addLayout(header)

        root.addSpacing(14)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setSpacing(14)
        c_lay.setContentsMargins(0, 0, 0, 0)

        wifi_ok = _check_network()
        c_lay.addWidget(_StatusCard("wifi.png", "WiFi", "WiFi 연결", "연결됨" if wifi_ok else "연결 안됨", wifi_ok))
        c_lay.addWidget(_StatusCard("server.png", "서버", "서버 통신", "통신 가능", True))
        c_lay.addWidget(_VolumeCard())
        c_lay.addWidget(_ControlCard())
        c_lay.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        root.addSpacing(8)

        ver = QLabel("Smart Medication Dispenser v1.0")
        ver.setFont(QFont("Sans Serif", 16))
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {_GRAY};")
        root.addWidget(ver)
