import sys

from PyQt5.QtCore import QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget

from config.settings import FULLSCREEN, SCHEDULE_POLL_SECONDS, SCREEN_HEIGHT, SCREEN_WIDTH
from ui.screens.auth_result import AuthResultScreen
from ui.screens.camera_view import CameraViewScreen
from ui.screens.complete import CompleteScreen
from ui.screens.dispensing import DispensingScreen
from ui.screens.fingerprint_register import FingerprintRegisterScreen
from ui.screens.home import HomeScreen
from ui.screens.medication import MedicationScreen
from ui.screens.medication_start import MedicationStartScreen
from ui.screens.register import RegisterScreen
from ui.screens.register_complete import RegisterCompleteScreen
from ui.screens.settings import SettingsScreen


def _new_session() -> dict:
    return {
        "sche_id": None,
        "face_verified": False,
        "dispensed": False,
        "action_verified": False,
        "similarity_score": 0.0,
    }


class _ScheduleSyncWorker(QThread):
    sync_done = pyqtSignal(list)

    def run(self):
        try:
            from scheduler.schedule import sync_schedules
            schedules = sync_schedules()
            self.sync_done.emit(schedules)
        except Exception:
            self.sync_done.emit([])


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Carefull")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.current_session: dict = _new_session()
        self._cached_schedules: list = []
        self._sync_worker: _ScheduleSyncWorker = None

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.screens = {
            "home":                 HomeScreen(self),
            "register":             RegisterScreen(self),
            "camera_view":          CameraViewScreen(self),
            "fingerprint_register": FingerprintRegisterScreen(self),
            "register_complete":    RegisterCompleteScreen(self),
            "medication_start":     MedicationStartScreen(self),
            "auth_result":          AuthResultScreen(self),
            "dispensing":           DispensingScreen(self),
            "medication":           MedicationScreen(self),
            "complete":             CompleteScreen(self),
            "settings":             SettingsScreen(self),
        }

        for screen in self.screens.values():
            self.stack.addWidget(screen)

        self.show_screen("home")
        self._start_schedule_polling()

    def show_screen(self, name: str):
        self.stack.setCurrentWidget(self.screens[name])

    # ── 스케줄 폴링 ──────────────────────────────────────────────────────────

    def _start_schedule_polling(self):
        self._trigger_sync()
        self._schedule_timer = QTimer(self)
        self._schedule_timer.timeout.connect(self._trigger_sync)
        self._schedule_timer.start(SCHEDULE_POLL_SECONDS * 1000)

    def _trigger_sync(self):
        if self._sync_worker and self._sync_worker.isRunning():
            return
        self._sync_worker = _ScheduleSyncWorker()
        self._sync_worker.sync_done.connect(self._on_sync_done)
        self._sync_worker.start()

    def _on_sync_done(self, schedules: list):
        if schedules:
            self._cached_schedules = schedules

        from scheduler.schedule import check_schedule
        due = check_schedule(self._cached_schedules or None)
        if not due:
            return

        # 홈 화면일 때만 자동으로 복약 시작
        if self.stack.currentWidget() != self.screens["home"]:
            return

        s = due[0]
        self.current_session = _new_session()
        self.current_session["sche_id"] = s.get("sche_id")
        self.show_screen("medication_start")


def run():
    app = QApplication(sys.argv)
    window = App()
    if FULLSCREEN:
        window.showFullScreen()
    else:
        window.show()
    sys.exit(app.exec_())
