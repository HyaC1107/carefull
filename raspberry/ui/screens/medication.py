from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.threads.behavior_thread import BehaviorThread, _SUCCESS_FRAMES

_MANUAL_TIMEOUT_MS = 60_000   # 60초 안에 복약 감지 안 되면 완료 처리


class MedicationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._thread = None
        self._timeout_timer = None
        self._build_ui()

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 50, 40, 50)
        root.setSpacing(0)

        icon = QLabel("🤲")
        icon.setFont(QFont("Sans Serif", 72))
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel("약을 복용해 주세요")
        title.setFont(QFont("Sans Serif", 30, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1a1a2e;")

        desc = QLabel("약을 손에 들고 입으로 가져가면\n자동으로 복약이 감지됩니다.")
        desc.setFont(QFont("Sans Serif", 19))
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #555;")

        # 감지 진행률 바
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, _SUCCESS_FRAMES)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(24)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #b0c4de;
                border-radius: 12px;
                background: #eef2ff;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 10px;
            }
        """)

        self._status_lbl = QLabel("복약을 감지하는 중...")
        self._status_lbl.setFont(QFont("Sans Serif", 18))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet("color: #888;")

        # 직접 완료 버튼 (감지 실패 대비)
        done_btn = QPushButton("복약 완료")
        done_btn.setMinimumHeight(64)
        done_btn.setFont(QFont("Sans Serif", 22))
        done_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        done_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 14px;
            }
            QPushButton:pressed { background-color: #218838; }
        """)
        done_btn.clicked.connect(self._on_intake)

        root.addStretch(1)
        root.addWidget(icon)
        root.addSpacing(16)
        root.addWidget(title)
        root.addSpacing(12)
        root.addWidget(desc)
        root.addStretch(1)
        root.addWidget(self._progress_bar)
        root.addSpacing(8)
        root.addWidget(self._status_lbl)
        root.addStretch(2)
        root.addWidget(done_btn)

    # ──────────────────────────────── 생명주기 ────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._progress_bar.setValue(0)
        self._status_lbl.setText("복약을 감지하는 중...")
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

    # ──────────────────────────────── 스레드 ─────────────────────────────────

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
        self._progress_bar.setValue(current)

    def _on_intake(self):
        self._stop_thread()
        if self._timeout_timer:
            self._timeout_timer.stop()
        if self._app:
            self._app.show_screen("complete")
