import time
import os

from PyQt5.QtCore import Qt, QRectF, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import (
    QPushButton, QSizePolicy, QVBoxLayout, QWidget, QLabel,
)

from config.settings import TTS_VOICE_PATH, ALARM_SOUND_PATH
from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

def _play_voice(filename: str):
    try:
        from hardware.alarm import play_voice
        play_voice(filename)
    except Exception:
        pass


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
                    # stop() 호출 후 detect 결과가 늦게 오는 경우 emit 방지
                    if self._running and detect_face(small):
                        self.face_detected.emit()
                        return
            except Exception:
                pass
            time.sleep(_FACE_DETECT_INTERVAL)

    def stop(self):
        self._running = False


class _BellWidget(QWidget):
    """알림 벨 아이콘 (주황 벨 + 분홍 도트)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(_fs(120), _fs(120))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        sc = self.width() / 120.0  # 스케일 비율

        pen = QPen(QColor(_ORANGE), _fs(4), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        body = QPainterPath()
        body.moveTo(cx, cy - 30 * sc)
        body.cubicTo(cx + 24 * sc, cy - 30 * sc, cx + 28 * sc, cy - 10 * sc, cx + 28 * sc, cy + 8 * sc)
        body.lineTo(cx - 28 * sc, cy + 8 * sc)
        body.cubicTo(cx - 28 * sc, cy - 10 * sc, cx - 24 * sc, cy - 30 * sc, cx, cy - 30 * sc)
        p.drawPath(body)

        p.drawArc(int(cx - 8 * sc), int(cy - 36 * sc), int(16 * sc), int(14 * sc), 0, 180 * 16)
        p.drawArc(int(cx - 10 * sc), int(cy + 6 * sc), int(20 * sc), int(12 * sc), 180 * 16, 180 * 16)

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#fb7185"))
        p.drawEllipse(QRectF(cx + 16 * sc, cy - 32 * sc, 14 * sc, 14 * sc))


class MedicationStartScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._face_thread: _FaceWatchThread = None
        self._show_time = 0.0  # 화면 표시 시점 기록
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"MedicationStartScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(_fs(32), 0, _fs(32), _fs(24))
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        bell = _BellWidget()
        root.addWidget(bell, alignment=Qt.AlignCenter)
        root.addSpacing(_fs(24))

        title = QLabel("약 드실 시간입니다")
        title.setFont(QFont("Sans Serif", _fs(56), QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_TEXT};")
        root.addWidget(title)

        root.addSpacing(_fs(10))

        self._sub_lbl = QLabel("카메라 앞에 서시면 자동으로 시작됩니다")
        self._sub_lbl.setFont(QFont("Sans Serif", _fs(36)))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setWordWrap(True)
        self._sub_lbl.setStyleSheet(f"color: {_ORANGE};")
        root.addWidget(self._sub_lbl)

        root.addStretch(2)

        start_btn = QPushButton("복약 프로세스 시작")
        start_btn.setMinimumHeight(_fs(72))
        start_btn.setFont(QFont("Sans Serif", _fs(34), QFont.Bold))
        start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_ORANGE};
                color: white;
                border: none;
                border-radius: {_fs(14)}px;
            }}
            QPushButton:pressed {{ background-color: #ea6c0a; }}
        """)
        start_btn.clicked.connect(self._go_auth)
        root.addWidget(start_btn)

    # ── 생명주기 ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._show_time = time.time()  # 진입 시점 기록

        # 1. 사용할 알림음 결정 (보호자 업로드 alarm.mp3 우선, 없으면 기본 default_alarm.mp3)
        active_alarm = "alarm.mp3" if os.path.exists(ALARM_SOUND_PATH) else "default_alarm.mp3"
        
        # 2. TTS 음성 존재 여부 확인
        has_tts = os.path.exists(TTS_VOICE_PATH)

        if has_tts:
            # TTS가 있으면: 알림음을 1.2초만 먼저 들려줌 (도입부)
            _play_voice(active_alarm)
            delay = 1200
        else:
            # TTS가 없으면: 알림음으로 루프 재생 시작
            _play_voice(active_alarm)
            delay = 4500  # 비차단 모드에서 루프 전환을 위한 대기

        self._alarm_loop_timer = QTimer(self)
        self._alarm_loop_timer.setSingleShot(True)
        self._alarm_loop_timer.timeout.connect(self._start_alarm_loop)
        self._alarm_loop_timer.start(delay)
        
        self._start_face_watch()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_face_watch()
        self._stop_alarm()
        if hasattr(self, "_alarm_loop_timer"):
            self._alarm_loop_timer.stop()

    # ── 알람 ─────────────────────────────────────────────────────────────────

    def _start_alarm_loop(self):
        if self.isVisible():
            self._start_alarm()

    def _start_alarm(self):
        """본 알람(루프) 재생: TTS가 있으면 TTS 재생, 없으면 결정된 알림음 재생."""
        try:
            from hardware.alarm import play_alarm
            # play_alarm은 내부적으로 alarm.mp3 -> voice.mp3 -> default 순으로 찾으므로
            # 순서를 명시적으로 처리하기 위해 파일명을 직접 지정
            if os.path.exists(TTS_VOICE_PATH):
                play_alarm("voice.mp3", loop=True)
            elif os.path.exists(ALARM_SOUND_PATH):
                play_alarm("alarm.mp3", loop=True)
            else:
                play_alarm("default_alarm.mp3", loop=True)
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
        if self._face_thread:
            # 시그널 먼저 끊어서 늦은 emit이 다른 화면에 영향 못 주게 함
            try:
                self._face_thread.face_detected.disconnect()
            except Exception:
                pass
            if self._face_thread.isRunning():
                self._face_thread.stop()
                self._face_thread.wait(1500)
        self._face_thread = None

    # ── 시그널 핸들러 ─────────────────────────────────────────────────────────

    def _on_face_detected(self):
        """얼굴 감지 → TTS 재생 여부에 맞춰 최소 대기 후 인증 화면으로."""
        has_tts = os.path.exists(TTS_VOICE_PATH)
        
        # TTS가 있으면 어르신이 내용을 충분히 인지하도록 최소 3.2초 대기
        # 없으면 기본 2초 대기
        min_wait = 3.2 if has_tts else 2.0
        
        elapsed = time.time() - self._show_time
        if elapsed < min_wait:
            remaining = int((min_wait - elapsed) * 1000)
            QTimer.singleShot(remaining, self._go_auth)
        else:
            self._go_auth()

    def _go_auth(self):
        # 화면이 바뀌었을 수도 있으므로(취소 등) 현재 활성 상태인지 체크
        if not self.isVisible():
            return
        self._stop_face_watch()
        self._stop_alarm()
        if self._app:
            self._app.screens["camera_view"].set_mode("auth")
            self._app.show_screen("camera_view")
