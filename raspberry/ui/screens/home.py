import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from config.settings import UI_TEST_MODE, DEVICE_UID

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


class _DeviceStatusWorker(QThread):
    status_ready = pyqtSignal(bool, bool)  # (is_paired, has_face)

    def run(self):
        if UI_TEST_MODE:
            self.status_ready.emit(True, False)
            return
        try:
            from api.client import fetch_device_status
            s = fetch_device_status()
            self.status_ready.emit(s["is_paired"], s["has_face"])
        except Exception:
            self.status_ready.emit(False, False)


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

    _STYLE_NORMAL = """
        QWidget {
            background-color: white;
            border: 2px solid #d0d5dd;
            border-radius: 14px;
        }
    """
    _STYLE_PRESS = """
        QWidget {
            background-color: #f0f4ff;
            border: 2px solid #aab0bb;
            border-radius: 14px;
        }
    """
    _STYLE_DISABLED = """
        QWidget {
            background-color: #f1f5f9;
            border: 2px solid #e2e8f0;
            border-radius: 14px;
        }
    """

    def __init__(self, png_name: str, fallback: str, text: str, callback, parent=None):
        super().__init__(parent)
        self._callback = callback
        self._enabled = True
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self._STYLE_NORMAL)

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

        self._text_lbl = QLabel(text)
        self._text_lbl.setFont(QFont("Sans Serif", 24))
        self._text_lbl.setAlignment(Qt.AlignCenter)
        self._text_lbl.setStyleSheet(f"background: transparent; border: none; color: {_DARK};")

        lay.addWidget(icon_lbl)
        lay.addWidget(self._text_lbl)

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        if enabled:
            self.setStyleSheet(self._STYLE_NORMAL)
            self._text_lbl.setStyleSheet(f"background: transparent; border: none; color: {_DARK};")
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setStyleSheet(self._STYLE_DISABLED)
            self._text_lbl.setStyleSheet("background: transparent; border: none; color: #94a3b8;")
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if not self._enabled:
            return
        self.setStyleSheet(self._STYLE_PRESS)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not self._enabled:
            return
        self.setStyleSheet(self._STYLE_NORMAL)
        self._callback()
        super().mouseReleaseEvent(event)


class HomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._status_worker: _DeviceStatusWorker = None
        self._build_ui()
        self._start_timers()

    def _build_ui(self):
        self.setStyleSheet(f"HomeScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
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
        time_label.setFont(QFont("Sans Serif", 20))
        time_label.setStyleSheet(f"color: {_GRAY}; background-color: {_BG}; border: none;")
        time_row.addWidget(clock_icon)
        time_row.addWidget(time_label)
        root.addLayout(time_row)

        root.addSpacing(6)

        # 큰 시계
        self._clock_lbl = QLabel()
        self._clock_lbl.setAlignment(Qt.AlignCenter)
        self._clock_lbl.setFont(QFont("Sans Serif", 96, QFont.Bold))
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
        self._badge_lbl.setFont(QFont("Sans Serif", 28))
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
        status_text.setFont(QFont("Sans Serif", 22))
        status_text.setStyleSheet(f"color: {_GREEN};")

        status_row.addWidget(dot)
        status_row.addWidget(status_text)
        root.addLayout(status_row)

        root.addStretch(2)

        # 버튼 2개 (가로 배치)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        self._btn_register = _MenuButton("register.png", "등록", "사용자 등록", lambda: self._go("register"))
        self._btn_register.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_register.setMinimumHeight(140)
        self._btn_register.hide()  # 기기 페어링 확인 전까지 숨김

        btn_settings = _MenuButton("settings.png", "설정", "설정", lambda: self._go("settings"))
        btn_settings.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_settings.setMinimumHeight(140)

        btn_row.addWidget(self._btn_register)
        btn_row.addWidget(btn_settings)
        root.addLayout(btn_row)

        root.addSpacing(10)

        # ── 테스트 단축 버튼 (1줄: 얼굴인증 / 사용자등록) ──────────────────
        test_row1 = QHBoxLayout()
        test_row1.setSpacing(10)

        btn_face_test = _MenuButton("camera_auth.png", "얼굴", "얼굴 인증 테스트", lambda: self._go_auth_test())
        btn_face_test.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_face_test.setMinimumHeight(96)
        btn_face_test.setStyleSheet("""
            QWidget { background-color: #eff6ff; border: 2px solid #93c5fd; border-radius: 14px; }
        """)

        btn_reg_test = _MenuButton("register.png", "등록", "사용자 등록", lambda: self._go("register"))
        btn_reg_test.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_reg_test.setMinimumHeight(96)
        btn_reg_test.setStyleSheet("""
            QWidget { background-color: #f5f0ff; border: 2px solid #c4b5fd; border-radius: 14px; }
        """)

        test_row1.addWidget(btn_face_test)
        test_row1.addWidget(btn_reg_test)
        root.addLayout(test_row1)

        root.addSpacing(10)

        # ── 테스트 단축 버튼 (2줄: 복약행위검증 / 지문인증) ────────────────
        test_row2 = QHBoxLayout()
        test_row2.setSpacing(10)

        btn_med_test = _MenuButton("medication.png", "복약", "복약행위 검증", lambda: self._go("medication"))
        btn_med_test.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_med_test.setMinimumHeight(96)
        btn_med_test.setStyleSheet("""
            QWidget { background-color: #f0fdf4; border: 2px solid #86efac; border-radius: 14px; }
        """)

        btn_fp_test = _MenuButton("fingerprint.png", "지문", "지문 인증", lambda: self._go("fingerprint_auth"))
        btn_fp_test.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_fp_test.setMinimumHeight(96)
        btn_fp_test.setStyleSheet("""
            QWidget { background-color: #fff7ed; border: 2px solid #fed7aa; border-radius: 14px; }
        """)

        test_row2.addWidget(btn_med_test)
        test_row2.addWidget(btn_fp_test)
        root.addLayout(test_row2)

        root.addSpacing(10)

        # ── 기기 UID 표시 (보호자가 웹 대시보드 기기 등록 시 입력) ──────────
        uid_text = DEVICE_UID or "(UID 미생성)"
        uid_lbl = QLabel(f"기기 UID:  {uid_text}")
        uid_lbl.setFont(QFont("Monospace", 15))
        uid_lbl.setAlignment(Qt.AlignCenter)
        uid_lbl.setStyleSheet("""
            color: #64748b;
            background-color: #e2e8f0;
            border-radius: 8px;
            padding: 5px 16px;
        """)
        root.addWidget(uid_lbl)

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

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_device_status()

    def _refresh_device_status(self):
        if self._status_worker and self._status_worker.isRunning():
            return
        self._status_worker = _DeviceStatusWorker()
        self._status_worker.status_ready.connect(self._on_status_ready)
        self._status_worker.start()

    def _on_status_ready(self, is_paired: bool, has_face: bool):
        if not is_paired:
            self._btn_register.hide()
        elif not has_face:
            self._btn_register.show()
            self._btn_register.set_enabled(True)
        else:
            self._btn_register.show()
            self._btn_register.set_enabled(False)

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)

    def _go_auth_test(self):
        if self._app:
            self._app.screens["camera_view"].set_mode("auth")
            self._app.show_screen("camera_view")
