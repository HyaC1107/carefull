import json
import os
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

_SCHEDULE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "schedule.json")
)


def _fmt_ampm(hour: int, minute: int) -> str:
    period = "오전" if hour < 12 else "오후"
    h12 = hour % 12 or 12
    return f"{period} {h12:02d}:{minute:02d}"


def _next_medication() -> str:
    try:
        with open(_SCHEDULE_PATH, "r", encoding="utf-8") as f:
            schedules = json.load(f)
    except Exception:
        return "정보 없음"

    now = datetime.now()
    now_min = now.hour * 60 + now.minute

    times = sorted(
        int(e["time"].split(":")[0]) * 60 + int(e["time"].split(":")[1])
        for e in schedules
        if "time" in e
    )

    if not times:
        return "없음"

    for t in times:
        if t > now_min:
            h, m = divmod(t, 60)
            return _fmt_ampm(h, m)

    h, m = divmod(times[0], 60)
    return f"내일 {_fmt_ampm(h, m)}"


class HomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()
        self._start_timers()

    # ──────────────────────────────── UI 구성 ────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 40, 32, 40)
        root.setSpacing(0)

        # 상태 뱃지 (상단 좌측)
        root.addWidget(self._build_status_badge(), alignment=Qt.AlignLeft)
        root.addStretch(1)

        # 시계
        self._clock_label = QLabel()
        self._clock_label.setAlignment(Qt.AlignCenter)
        self._clock_label.setFont(QFont("Sans Serif", 56, QFont.Bold))
        self._clock_label.setStyleSheet("color: #1a1a2e;")
        root.addWidget(self._clock_label)

        root.addSpacing(28)

        # 다음 복약 카드
        card, self._next_med_label = self._build_medication_card()
        root.addWidget(card)

        root.addStretch(2)

        # 버튼 3개
        for text, color, target, size in [
            ("사용자 등록",              "#4a90d9", "register",    22),
            ("설정",                    "#6c757d", "settings",    22),
        ]:
            root.addSpacing(12)
            root.addWidget(self._build_button(text, color, target, size))

        root.addSpacing(12)
        test_btn = self._build_button("복약 프로세스 시작 (테스트)", "#e07b39", "camera_view", 18)
        test_btn.clicked.disconnect()
        test_btn.clicked.connect(self._start_auth)
        root.addWidget(test_btn)

    def _build_status_badge(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        dot = QLabel("●")
        dot.setFont(QFont("Sans Serif", 13))
        dot.setStyleSheet("color: #28a745;")

        label = QLabel("정상 작동 중")
        label.setFont(QFont("Sans Serif", 16))
        label.setStyleSheet("color: #28a745;")

        lay.addWidget(dot)
        lay.addWidget(label)
        return w

    def _build_medication_card(self) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f0f4ff;
                border: 2px solid #b0c4de;
                border-radius: 18px;
            }
        """)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(24, 22, 24, 22)
        lay.setSpacing(10)

        title = QLabel("다음 복약 시간")
        title.setFont(QFont("Sans Serif", 18))
        title.setStyleSheet("color: #555555; border: none;")
        title.setAlignment(Qt.AlignCenter)

        time_label = QLabel(_next_medication())
        time_label.setFont(QFont("Sans Serif", 36, QFont.Bold))
        time_label.setStyleSheet("color: #1a1a2e; border: none;")
        time_label.setAlignment(Qt.AlignCenter)

        lay.addWidget(title)
        lay.addWidget(time_label)
        return card, time_label

    def _build_button(self, text: str, color: str, target: str, font_size: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(64)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setFont(QFont("Sans Serif", font_size))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 14px;
                padding: 8px 16px;
            }}
            QPushButton:pressed {{
                opacity: 0.85;
                background-color: {color}bb;
            }}
        """)
        btn.clicked.connect(lambda: self._go(target))
        return btn

    # ──────────────────────────────── 타이머 ─────────────────────────────────

    def _start_timers(self):
        self._update_clock()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        # 다음 복약 카드는 1분마다 갱신
        self._med_timer = QTimer(self)
        self._med_timer.timeout.connect(self._update_medication)
        self._med_timer.start(60_000)

    def _update_clock(self):
        now = datetime.now()
        self._clock_label.setText(_fmt_ampm(now.hour, now.minute))

    def _update_medication(self):
        self._next_med_label.setText(_next_medication())

    # ──────────────────────────────── 화면 전환 ───────────────────────────────

    def _start_auth(self):
        if self._app:
            self._app.screens["camera_view"].set_mode("auth")
            self._app.show_screen("camera_view")

    def _go(self, screen: str):
        if self._app:
            self._app.show_screen(screen)
