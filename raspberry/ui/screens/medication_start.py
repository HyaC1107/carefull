import time

from PyQt5.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QLabel,
)

_BG     = "#fff8e8"
_ORANGE = "#f97316"
_TEXT   = "#7c4a1a"

_FACE_DETECT_INTERVAL = 0.25   # 얼굴 감지 주기(초)


class _FaceWatchThread(QThread):
    """카메라를 주기적으로 확인해 얼굴이 감지되면 시그널 발생."""
    face_detected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def run(self):
        from camera.camera import get_frame
        from face_detection.mediapipe_detector import detect_face
        import cv2

        self._running = True
        while self._running:
            try:
                frame = get_frame()
                if frame is not None:
                    small = cv2.resize(frame, (320, 240))
                    if detect_face(small):
                        self.face_detected.emit()
                        return   # 감지 후 스레드 종료
            except Exception:
                pass
            time.sleep(_FACE_DETECT_INTERVAL)

    def stop(self):
        self._running = False


class _BellWidget(QWidget):
    """알림 벨 아이콘 (주황 벨 + 분홍 도트)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2

        pen = QPen(QColor(_ORANGE), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        body = QPainterPath()
        body.moveTo(cx, cy - 30)
        body.cubicTo(cx + 24, cy - 30, cx + 28, cy - 10, cx + 28, cy + 8)
        body.lineTo(cx - 28, cy + 8)
        body.cubicTo(cx - 28, cy - 10, cx - 24, cy - 30, cx, cy - 30)
        p.drawPath(body)

        p.drawArc(int(cx - 8), int(cy - 36), 16, 14, 0, 180 * 16)
        p.drawArc(int(cx - 10), int(cy + 6), 20, 12, 180 * 16, 180 * 16)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#fb7185"))
        p.drawEllipse(QRectF(cx + 16, cy - 32, 14, 14))


class MedicationStartScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._face_thread: _FaceWatchThread = None
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"MedicationStartScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 0, 32, 24)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        bell = _BellWidget()
        root.addWidget(bell, alignment=Qt.AlignCenter)
        root.addSpacing(24)

        title = QLabel("약 드실 시간입니다")
        title.setFont(QFont("Sans Serif", 48, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_TEXT};")
        root.addWidget(title)

        root.addSpacing(10)

        self._sub_lbl = QLabel("카메라 앞에 서시면 자동으로 시작됩니다")
        self._sub_lbl.setFont(QFont("Sans Serif", 30))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet(f"color: {_ORANGE};")
        root.addWidget(self._sub_lbl)

        root.addStretch(2)

        start_btn = QPushButton("복약 프로세스 시작")
        start_btn.setMinimumHeight(60)
        start_btn.setFont(QFont("Sans Serif", 28, QFont.Bold))
        start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_ORANGE};
                color: white;
                border: none;
                border-radius: 14px;
            }}
            QPushButton:pressed {{ background-color: #ea6c0a; }}
        """)
        start_btn.clicked.connect(self._go_auth)
        root.addWidget(start_btn)

    # ── 생명주기 ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._start_alarm()
        self._start_face_watch()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_face_watch()
        self._stop_alarm()

    # ── 알람 ─────────────────────────────────────────────────────────────────

    def _start_alarm(self):
        try:
            from hardware.alarm import play_alarm
            play_alarm(loop=True)
        except Exception as e:
            print(f"[ALARM] 재생 실패: {e}")

    def _stop_alarm(self):
        try:
            from hardware.alarm import stop_alarm
            stop_alarm()
        except Exception as e:
            print(f"[ALARM] 정지 실패: {e}")

    # ── 얼굴 감지 스레드 ──────────────────────────────────────────────────────

    def _start_face_watch(self):
        self._stop_face_watch()
        self._face_thread = _FaceWatchThread(parent=self)
        self._face_thread.face_detected.connect(self._on_face_detected)
        self._face_thread.start()

    def _stop_face_watch(self):
        if self._face_thread and self._face_thread.isRunning():
            self._face_thread.stop()
            self._face_thread.wait(1000)
        self._face_thread = None

    # ── 시그널 핸들러 ─────────────────────────────────────────────────────────

    def _on_face_detected(self):
        """얼굴 감지 → 알람 끄고 인증 화면으로."""
        self._go_auth()

    def _go_auth(self):
        self._stop_face_watch()
        self._stop_alarm()
        if self._app:
            self._app.screens["camera_view"].set_mode("auth")
            self._app.show_screen("camera_view")
