import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from config.settings import UI_TEST_MODE

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_SCHEDULE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "schedule.json")
)

_BG = "#f2f3f7"
_DARK = "#1e293b"
_GRAY = "#64748b"
_GREEN = "#22c55e"
_BLUE = "#3b82f6"


def _fmt_ampm(hour: int, minute: int) -> str:
    period = "오전" if hour < 12 else "오후"
    h12 = hour % 12 or 12
    return f"{period} {h12:02d}:{minute:02d}"


def _next_medication() -> str:
    try:
        with open(_SCHEDULE_PATH, "r", encoding="utf-8") as f:
            schedules = json.load(f)
    except Exception:
        return "--:--"

    now = datetime.now()
    now_min = now.hour * 60 + now.minute
    times = []
    for e in schedules:
        # API 포맷(time_to_take) 및 레거시 포맷(time) 모두 지원
        t = e.get("time_to_take") or e.get("time", "")
        t = str(t)[:5]  # "HH:MM:SS" → "HH:MM"
        try:
            h, m = map(int, t.split(":"))
            times.append(h * 60 + m)
        except Exception:
            continue
    times.sort()
    if not times:
        return "--:--"
    for t in times:
        if t > now_min:
            h, m = divmod(t, 60)
            return f"{h:02d}:{m:02d}"
    h, m = divmod(times[0], 60)
    return f"{h:02d}:{m:02d}"


class _MenuButton(QWidget):
    """아이콘(PNG 또는 텍스트) + 텍스트 세로 배치 아웃라인 버튼."""

    def __init__(self, png_name: str, fallback: str, text: str, callback, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #d0d5dd;
                border-radius: 14px;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 18, 16, 18)
        lay.setSpacing(6)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        png_path = os.path.join(_ICONS_DIR, png_name)
        if os.path.exists(png_path):
            pix = QPixmap(png_path).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText(fallback)
            icon_lbl.setFont(QFont("Sans Serif", 22))

        text_lbl = QLabel(text)
        text_lbl.setFont(QFont("Sans Serif", 16))
        text_lbl.setAlignment(Qt.AlignCenter)
        text_lbl.setStyleSheet(f"background: transparent; border: none; color: {_DARK};")

        lay.addWidget(icon_lbl)
        lay.addWidget(text_lbl)
        self._callback = callback

    def mousePressEvent(self, event):
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f4ff;
                border: 2px solid #aab0bb;
                border-radius: 14px;
            }
        """)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 2px solid #d0d5dd;
                border-radius: 14px;
            }
        """)
        self._callback()
        super().mouseReleaseEvent(event)


class HomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()
        self._start_timers()

    def _build_ui(self):
        self.setStyleSheet(f"HomeScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(0)

        root.addStretch(2)

        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        time_row.setAlignment(Qt.AlignCenter)
        clock_icon = QLabel()
        clock_icon.setStyleSheet("background: transparent; border: none;")
        _clock_path = os.path.join(_ICONS_DIR, "clock.png")
        if os.path.exists(_clock_path):
            _pix = QPixmap(_clock_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            clock_icon.setPixmap(_pix)
        time_label = QLabel("현재 시간")
        time_label.setFont(QFont("Sans Serif", 13))
        time_label.setStyleSheet(f"color: {_GRAY}; background-color: {_BG}; border: none;")
        time_row.addWidget(clock_icon)
        time_row.addWidget(time_label)
        root.addLayout(time_row)

        root.addSpacing(6)

        # 큰 시계
        self._clock_lbl = QLabel()
        self._clock_lbl.setAlignment(Qt.AlignCenter)
        self._clock_lbl.setFont(QFont("Sans Serif", 52, QFont.Bold))
        self._clock_lbl.setStyleSheet(f"""
            color: {_DARK};
            background-color: {_BG};
            border-radius: 16px;
            padding: 8px 16px;
        """)
        root.addWidget(self._clock_lbl)

        root.addSpacing(14)

        # 다음 복약 뱃지
        self._badge_lbl = QLabel()
        self._badge_lbl.setAlignment(Qt.AlignCenter)
        self._badge_lbl.setFont(QFont("Sans Serif", 16))
        self._badge_lbl.setStyleSheet(f"""
            color: #1d4ed8;
            background-color: white;
            border: 2px solid #93c5fd;
            border-radius: 20px;
            padding: 6px 24px;
        """)
        root.addWidget(self._badge_lbl, alignment=Qt.AlignCenter)

        root.addSpacing(14)

        # 상태 뱃지
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        status_row.setAlignment(Qt.AlignCenter)

        dot = QLabel("●")
        dot.setFont(QFont("Sans Serif", 11))
        dot.setStyleSheet(f"color: {_GREEN};")

        status_text = QLabel("정상 작동 중")
        status_text.setFont(QFont("Sans Serif", 14))
        status_text.setStyleSheet(f"color: {_GREEN};")

        status_row.addWidget(dot)
        status_row.addWidget(status_text)
        root.addLayout(status_row)

        root.addStretch(3)

        # 버튼 2개 (가로 배치)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        btn_register = _MenuButton("register.png", "등록", "사용자 등록", lambda: self._go("register"))
        btn_register.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_register.setMinimumHeight(96)

        btn_settings = _MenuButton("settings.png", "설정", "설정", lambda: self._go("settings"))
        btn_settings.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_settings.setMinimumHeight(96)

        btn_row.addWidget(btn_register)
        btn_row.addWidget(btn_settings)
        root.addLayout(btn_row)

        if UI_TEST_MODE:
            root.addSpacing(10)
            test_row = QHBoxLayout()
            test_row.setSpacing(14)

            btn_face_test = _MenuButton("camera_auth.png", "얼굴", "얼굴 인증 테스트", lambda: self._go_auth_test())
            btn_face_test.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn_face_test.setMinimumHeight(96)
            btn_face_test.setStyleSheet("""
                QWidget {
                    background-color: #eff6ff;
                    border: 2px solid #93c5fd;
                    border-radius: 14px;
                }
            """)

            btn_med_test = _MenuButton("medication.png", "복약", "복약행위 테스트", lambda: self._go("medication"))
            btn_med_test.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn_med_test.setMinimumHeight(96)
            btn_med_test.setStyleSheet("""
                QWidget {
                    background-color: #f0fdf4;
                    border: 2px solid #86efac;
                    border-radius: 14px;
                }
            """)

            test_row.addWidget(btn_face_test)
            test_row.addWidget(btn_med_test)
            root.addLayout(test_row)

    def _start_timers(self):
        self._update_clock()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        self._med_timer = QTimer(self)
        self._med_timer.timeout.connect(self._update_badge)
        self._med_timer.start(60_000)

    def _update_clock(self):
        now = datetime.now()
        self._clock_lbl.setText(_fmt_ampm(now.hour, now.minute))
        self._update_badge()

    def _update_badge(self):
        t = _next_medication()
        self._badge_lbl.setText(f"다음 복약   {t}")

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)

    def _go_auth_test(self):
        if self._app:
            self._app.screens["camera_view"].set_mode("auth")
            self._app.show_screen("camera_view")
