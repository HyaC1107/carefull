"""
복약 알림 스케줄 테스트
  실행: python -m tests.test_schedule_notification  (raspberry/ 루트에서)

기능:
  - 서버에서 스케줄 동기화 후 현재 시각에 맞는 스케줄 표시
  - "지금 트리거" 버튼으로 강제 알림 발생 테스트
  - 30초 주기 폴링 시뮬레이션 (버튼으로 수동 폴링 가능)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QVBoxLayout, QWidget,
)

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN


class _SyncWorker(QThread):
    done = pyqtSignal(list)

    def run(self):
        try:
            from scheduler.schedule import sync_schedules
            schedules = sync_schedules()
        except Exception as e:
            print(f"[SYNC ERROR] {e}")
            schedules = []
        self.done.emit(schedules)


class ScheduleTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("복약 알림 스케줄 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet("background: #f0fdf4;")
        self._schedules = []
        self._worker = None
        self._build_ui()
        self._sync()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        title = QLabel("복약 알림 스케줄 테스트")
        title.setFont(QFont("Sans Serif", 38, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #15803d;")
        root.addWidget(title)

        self._time_lbl = QLabel(self._now_str())
        self._time_lbl.setFont(QFont("Sans Serif", 24))
        self._time_lbl.setAlignment(Qt.AlignCenter)
        self._time_lbl.setStyleSheet("color: #64748b;")
        root.addWidget(self._time_lbl)

        self._time_timer = QTimer(self)
        self._time_timer.timeout.connect(lambda: self._time_lbl.setText(self._now_str()))
        self._time_timer.start(1000)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        sync_btn = QPushButton("서버 동기화")
        sync_btn.setFont(QFont("Sans Serif", 22, QFont.Bold))
        sync_btn.setMinimumHeight(64)
        sync_btn.setStyleSheet("""
            QPushButton { background: #3b82f6; color: white; border-radius: 12px; }
            QPushButton:pressed { background: #2563eb; }
        """)
        sync_btn.clicked.connect(self._sync)
        btn_row.addWidget(sync_btn)

        check_btn = QPushButton("지금 체크")
        check_btn.setFont(QFont("Sans Serif", 22, QFont.Bold))
        check_btn.setMinimumHeight(64)
        check_btn.setStyleSheet("""
            QPushButton { background: #16a34a; color: white; border-radius: 12px; }
            QPushButton:pressed { background: #15803d; }
        """)
        check_btn.clicked.connect(self._check_now)
        btn_row.addWidget(check_btn)

        force_btn = QPushButton("강제 트리거")
        force_btn.setFont(QFont("Sans Serif", 22, QFont.Bold))
        force_btn.setMinimumHeight(64)
        force_btn.setStyleSheet("""
            QPushButton { background: #f97316; color: white; border-radius: 12px; }
            QPushButton:pressed { background: #ea580c; }
        """)
        force_btn.clicked.connect(self._force_trigger)
        btn_row.addWidget(force_btn)

        root.addLayout(btn_row)

        self._status_lbl = QLabel("동기화 중...")
        self._status_lbl.setFont(QFont("Sans Serif", 22))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet("color: #3b82f6;")
        root.addWidget(self._status_lbl)

        # 스케줄 목록
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_lay = QVBoxLayout(self._list_widget)
        self._list_lay.setSpacing(8)
        self._list_lay.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._list_widget)
        root.addWidget(scroll, stretch=1)

    def _now_str(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _sync(self):
        self._status_lbl.setText("서버 동기화 중...")
        self._worker = _SyncWorker(parent=self)
        self._worker.done.connect(self._on_synced)
        self._worker.start()

    def _on_synced(self, schedules: list):
        self._schedules = schedules
        self._status_lbl.setText(f"동기화 완료: 스케줄 {len(schedules)}건")
        self._status_lbl.setStyleSheet("color: #16a34a;")
        self._rebuild_list(schedules)

    def _rebuild_list(self, schedules: list):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not schedules:
            lbl = QLabel("등록된 스케줄이 없습니다")
            lbl.setFont(QFont("Sans Serif", 22))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #94a3b8;")
            self._list_lay.addWidget(lbl)
            return

        for s in schedules:
            row = QFrame()
            row.setStyleSheet("QFrame { background: white; border-radius: 12px; }")
            lay = QHBoxLayout(row)
            lay.setContentsMargins(20, 12, 20, 12)
            lay.setSpacing(16)

            time_lbl = QLabel(str(s.get("time_to_take", ""))[:5])
            time_lbl.setFont(QFont("Sans Serif", 28, QFont.Bold))
            time_lbl.setStyleSheet("color: #3b82f6;")
            lay.addWidget(time_lbl)

            name_lbl = QLabel(s.get("medi_name", f"ID {s.get('sche_id', '?')}"))
            name_lbl.setFont(QFont("Sans Serif", 22))
            name_lbl.setStyleSheet("color: #1e293b;")
            lay.addWidget(name_lbl)

            lay.addStretch()

            status_lbl = QLabel(s.get("status", ""))
            status_lbl.setFont(QFont("Sans Serif", 20))
            status_lbl.setStyleSheet("color: #64748b;")
            lay.addWidget(status_lbl)

            self._list_lay.addWidget(row)

        self._list_lay.addStretch()

    def _check_now(self):
        from scheduler.schedule import check_schedule
        due = check_schedule(self._schedules)
        if due:
            names = ", ".join(s.get("medi_name", f"ID {s.get('sche_id')}") for s in due)
            self._status_lbl.setText(f"✓ 트리거 대상: {names}")
            self._status_lbl.setStyleSheet("color: #f97316;")
        else:
            self._status_lbl.setText("현재 트리거할 스케줄 없음")
            self._status_lbl.setStyleSheet("color: #64748b;")

    def _force_trigger(self):
        """스케줄 시간 무시하고 첫 번째 스케줄을 강제 트리거."""
        if not self._schedules:
            self._status_lbl.setText("동기화된 스케줄이 없습니다")
            self._status_lbl.setStyleSheet("color: #dc2626;")
            return
        s = self._schedules[0]
        name = s.get("medi_name", f"sche_id={s.get('sche_id')}")
        self._status_lbl.setText(f"강제 트리거: {name}")
        self._status_lbl.setStyleSheet("color: #f97316; font-weight: bold;")
        # 알람 재생으로 알림 확인
        try:
            from hardware.alarm import play_alarm
            play_alarm()
            QTimer.singleShot(3000, lambda: __import__("hardware.alarm", fromlist=["stop_alarm"]).stop_alarm())
        except Exception as e:
            self._status_lbl.setText(f"알람 오류: {e}")


def main():
    app = QApplication(sys.argv)
    window = ScheduleTestWindow()
    if FULLSCREEN:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
