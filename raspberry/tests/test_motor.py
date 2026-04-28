"""
스텝모터 단위 테스트 — 실제 GPIO가 없으면 모의 실행
  실행: python -m tests.test_motor  (raspberry/ 루트에서)

버튼 설명:
  절반 회전(256스텝): 짧게 동작 확인
  전체 회전(512스텝): dispense_medicine() 전체 흐름 확인
  역방향(-256스텝): 모터 방향 확인
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, FULLSCREEN


class _MotorWorker(QThread):
    status = pyqtSignal(str)
    done   = pyqtSignal(bool)

    def __init__(self, steps: int, parent=None):
        super().__init__(parent)
        self._steps = steps

    def run(self):
        self.status.emit(f"모터 구동 중... ({self._steps}스텝)")
        try:
            from hardware.motor import _run_step_motor
            _run_step_motor(self._steps, delay=0.002)
            self.status.emit("완료")
            self.done.emit(True)
        except Exception as e:
            self.status.emit(f"오류: {e}")
            self.done.emit(False)


class _FullDispenseWorker(QThread):
    status = pyqtSignal(str)
    done   = pyqtSignal(bool)

    def run(self):
        self.status.emit("dispense_medicine() 실행 중...")
        try:
            from hardware.motor import dispense_medicine
            result = dispense_medicine(user="test_user")
            self.status.emit("완료" if result else "실패 반환")
            self.done.emit(result)
        except Exception as e:
            self.status.emit(f"오류: {e}")
            self.done.emit(False)


class MotorTestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("스텝모터 테스트")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet("background: #f0f4ff;")
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 48, 48, 48)
        root.setSpacing(24)
        root.setAlignment(Qt.AlignCenter)

        title = QLabel("스텝모터 단위 테스트")
        title.setFont(QFont("Sans Serif", 44, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #1e3a5f;")
        root.addWidget(title)

        self._status_lbl = QLabel("버튼을 눌러 테스트하세요")
        self._status_lbl.setFont(QFont("Sans Serif", 28))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet("color: #3b82f6;")
        root.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(16)

        for label, steps in [("절반 회전", 256), ("전체 회전", 512), ("역방향", -256)]:
            btn = QPushButton(label)
            btn.setFont(QFont("Sans Serif", 26, QFont.Bold))
            btn.setMinimumHeight(80)
            btn.setStyleSheet("""
                QPushButton { background: #3b82f6; color: white; border-radius: 16px; }
                QPushButton:pressed { background: #2563eb; }
                QPushButton:disabled { background: #93c5fd; }
            """)
            btn.clicked.connect(lambda _, s=steps: self._run_motor(s))
            btn_row.addWidget(btn)
            setattr(self, f"_btn_{abs(steps)}{'r' if steps < 0 else ''}", btn)

        root.addLayout(btn_row)

        dispense_btn = QPushButton("전체 플로우 (dispense_medicine)")
        dispense_btn.setFont(QFont("Sans Serif", 26, QFont.Bold))
        dispense_btn.setMinimumHeight(80)
        dispense_btn.setStyleSheet("""
            QPushButton { background: #16a34a; color: white; border-radius: 16px; }
            QPushButton:pressed { background: #15803d; }
            QPushButton:disabled { background: #86efac; }
        """)
        dispense_btn.clicked.connect(self._run_full)
        root.addWidget(dispense_btn)
        self._dispense_btn = dispense_btn

        self._result_lbl = QLabel("")
        self._result_lbl.setFont(QFont("Sans Serif", 36, QFont.Bold))
        self._result_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._result_lbl)

    def _set_buttons_enabled(self, enabled: bool):
        for attr in vars(self):
            if attr.startswith("_btn_") or attr == "_dispense_btn":
                getattr(self, attr).setEnabled(enabled)

    def _run_motor(self, steps: int):
        if self._worker and self._worker.isRunning():
            return
        self._result_lbl.setText("")
        self._set_buttons_enabled(False)
        self._worker = _MotorWorker(steps, parent=self)
        self._worker.status.connect(self._status_lbl.setText)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _run_full(self):
        if self._worker and self._worker.isRunning():
            return
        self._result_lbl.setText("")
        self._set_buttons_enabled(False)
        self._worker = _FullDispenseWorker(parent=self)
        self._worker.status.connect(self._status_lbl.setText)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, success: bool):
        self._set_buttons_enabled(True)
        if success:
            self._result_lbl.setText("✓ 성공")
            self._result_lbl.setStyleSheet("color: #16a34a;")
        else:
            self._result_lbl.setText("✗ 실패")
            self._result_lbl.setStyleSheet("color: #dc2626;")


def main():
    app = QApplication(sys.argv)
    window = MotorTestWindow()
    if FULLSCREEN:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
