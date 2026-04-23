from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QWidget


class StatusBadge(QWidget):
    def __init__(self, text: str = "정상 작동 중", color: str = "#28a745", parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._dot = QLabel("●")
        self._dot.setFont(QFont("Sans Serif", 11))

        self._label = QLabel(text)
        self._label.setFont(QFont("Sans Serif", 14))

        lay.addWidget(self._dot)
        lay.addWidget(self._label)

        self.set_color(color)

    def set_status(self, text: str, color: str):
        self._label.setText(text)
        self.set_color(color)

    def set_color(self, color: str):
        style = f"color: {color};"
        self._dot.setStyleSheet(style)
        self._label.setStyleSheet(style)
