"""
알람(음성 재생) 단위 테스트
  실행: python -m tests.test_alarm  (raspberry/ 루트에서)

  - 기본 알림음(default_voice.mp3) 재생
  - 재생 중 정지 테스트
  - 음성 파일이 없으면 경로 경고를 표시하고 계속
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN, VOICES_DIR


class AlarmTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("알람 단위 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet("background: #fff7ed;")
        self._playing = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 48, 48, 48)
        root.setSpacing(28)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel("알람 단위 테스트")
        title.setFont(QFont("Sans Serif", 44, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #7c3aed;")
        root.addWidget(title)

        default_path = os.path.join(VOICES_DIR, "default_voice.mp3")
        file_exists = os.path.exists(default_path)
        path_lbl = QLabel(
            f"기본 음성 파일: {default_path}\n{'✓ 파일 존재' if file_exists else '✗ 파일 없음 — 재생 시 오류 예상'}"
        )
        path_lbl.setFont(QFont("Sans Serif", 20))
        path_lbl.setAlignment(Qt.AlignCenter)
        path_lbl.setStyleSheet(f"color: {'#16a34a' if file_exists else '#dc2626'};")
        root.addWidget(path_lbl)

        self._status_lbl = QLabel("대기 중")
        self._status_lbl.setFont(QFont("Sans Serif", 28))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet("color: #7c3aed;")
        root.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(24)

        self._play_btn = QPushButton("▶  알람 재생")
        self._play_btn.setFont(QFont("Sans Serif", 28, QFont.Bold))
        self._play_btn.setMinimumHeight(80)
        self._play_btn.setStyleSheet("""
            QPushButton { background: #7c3aed; color: white; border-radius: 16px; }
            QPushButton:pressed { background: #6d28d9; }
        """)
        self._play_btn.clicked.connect(self._play)
        btn_row.addWidget(self._play_btn)

        stop_btn = QPushButton("■  정지")
        stop_btn.setFont(QFont("Sans Serif", 28, QFont.Bold))
        stop_btn.setMinimumHeight(80)
        stop_btn.setStyleSheet("""
            QPushButton { background: #dc2626; color: white; border-radius: 16px; }
            QPushButton:pressed { background: #b91c1c; }
        """)
        stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(stop_btn)

        root.addLayout(btn_row)

    def _play(self):
        from hardware.alarm import play_alarm
        self._status_lbl.setText("재생 중...")
        self._status_lbl.setStyleSheet("color: #7c3aed;")
        try:
            play_alarm()
            self._status_lbl.setText("✓ 재생 시작됨 (mpg123 프로세스)")
        except Exception as e:
            self._status_lbl.setText(f"✗ 오류: {e}")
            self._status_lbl.setStyleSheet("color: #dc2626;")

    def _stop(self):
        from hardware.alarm import stop_alarm
        stop_alarm()
        self._status_lbl.setText("정지됨")
        self._status_lbl.setStyleSheet("color: #64748b;")


def main():
    app = QApplication(sys.argv)
    window = AlarmTestWindow()
    if FULLSCREEN:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
