import cv2
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import (
    QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt5.QtWidgets import QWidget


class CameraCardWidget(QWidget):
    """둥근 카드 형태의 카메라 뷰 + 점선 원 오버레이."""

    def __init__(self, dash_color: str = "#7c3aed", parent=None):
        super().__init__(parent)
        self._frame = None
        self._dash_color = QColor(dash_color)

    def set_dash_color(self, color: str):
        self._dash_color = QColor(color)
        self.update()

    def update_frame(self, bgr_frame):
        self._frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 전체화면 여부에 따라 모서리 radius 결정
        radius = 0 if (self.width() >= 800 and self.height() >= 400) else 16
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), radius, radius)
        p.setClipPath(clip)
        p.fillRect(self.rect(), QColor("#1e2235"))

        if self._frame is not None:
            h, w, ch = self._frame.shape
            img = QImage(self._frame.data, w, h, ch * w, QImage.Format_RGB888)
            pix = QPixmap.fromImage(img).scaled(
                self.width(), self.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            ox = (self.width() - pix.width()) // 2
            oy = (self.height() - pix.height()) // 2
            p.drawPixmap(ox, oy, pix)

        p.setClipping(False)

        # 점선 원
        pen = QPen(self._dash_color, 3, Qt.CustomDashLine)
        pen.setDashPattern([8, 5])
        p.setPen(pen)
        cx = self.width() / 2
        cy = self.height() / 2
        r = min(self.width(), self.height()) * 0.36
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

