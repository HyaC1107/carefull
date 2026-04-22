import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QScrollArea, QVBoxLayout, QWidget,
)


def _row(label: str, value: str) -> QFrame:
    frame = QFrame()
    frame.setStyleSheet("""
        QFrame {
            background-color: #f8f9ff;
            border: 1px solid #dde3f0;
            border-radius: 10px;
        }
    """)
    lay = QHBoxLayout(frame)
    lay.setContentsMargins(20, 14, 20, 14)

    lbl = QLabel(label)
    lbl.setFont(QFont("Sans Serif", 18))
    lbl.setStyleSheet("color: #555; border: none;")

    val = QLabel(value)
    val.setFont(QFont("Sans Serif", 18, QFont.Bold))
    val.setStyleSheet("color: #1a1a2e; border: none;")
    val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    lay.addWidget(lbl, stretch=1)
    lay.addWidget(val)
    return frame


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._build_ui()

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 40, 32, 40)
        root.setSpacing(0)

        # 제목
        title = QLabel("설정")
        title.setFont(QFont("Sans Serif", 30, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a2e;")
        root.addWidget(title)
        root.addSpacing(24)

        # 설정 값 목록 (스크롤)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        c_lay = QVBoxLayout(content)
        c_lay.setSpacing(12)
        c_lay.setContentsMargins(0, 0, 0, 0)

        rows = self._load_settings()
        for label, value in rows:
            c_lay.addWidget(_row(label, value))
        c_lay.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        root.addSpacing(20)

        # 홈으로
        back_btn = QPushButton("홈으로")
        back_btn.setMinimumHeight(64)
        back_btn.setFont(QFont("Sans Serif", 22))
        back_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90d9;
                color: white;
                border: none;
                border-radius: 14px;
            }
            QPushButton:pressed { background-color: #3a7bc8; }
        """)
        back_btn.clicked.connect(lambda: self._app.show_screen("home"))
        root.addWidget(back_btn)

    # ──────────────────────────────── 설정 읽기 ──────────────────────────────

    @staticmethod
    def _load_settings() -> list[tuple[str, str]]:
        return [
            ("얼굴 인식 임계값",
             os.getenv("CAREFULL_FACE_MATCH_THRESHOLD", "0.8")),
            ("인증 재시도 횟수",
             os.getenv("CAREFULL_AUTH_RETRY_COUNT", "5") + " 회"),
            ("스케줄 확인 간격",
             os.getenv("CAREFULL_SCHEDULE_POLL_SECONDS", "30") + " 초"),
            ("카메라 해상도",
             f"{os.getenv('CAREFULL_CAMERA_WIDTH', '640')} × "
             f"{os.getenv('CAREFULL_CAMERA_HEIGHT', '480')}"),
            ("카메라 워밍업",
             os.getenv("CAREFULL_CAMERA_WARMUP_SECONDS", "2.0") + " 초"),
        ]
