import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget

from ui.screens.home import HomeScreen
from ui.screens.register import RegisterScreen
from ui.screens.camera_view import CameraViewScreen
from ui.screens.auth_result import AuthResultScreen
from ui.screens.dispensing import DispensingScreen
from ui.screens.medication import MedicationScreen
from ui.screens.complete import CompleteScreen
from ui.screens.settings import SettingsScreen


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Carefull")
        self.setFixedSize(1024, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.screens = {
            "home": HomeScreen(self),
            "register": RegisterScreen(self),
            "camera_view": CameraViewScreen(self),
            "auth_result": AuthResultScreen(self),
            "dispensing": DispensingScreen(self),
            "medication": MedicationScreen(self),
            "complete": CompleteScreen(self),
            "settings": SettingsScreen(self),
        }

        for screen in self.screens.values():
            self.stack.addWidget(screen)

        self.show_screen("home")

    def show_screen(self, name: str):
        self.stack.setCurrentWidget(self.screens[name])


def run():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())
