"""
복약행위 감지 파라미터 튜닝 도구  (PyQt5 버전)
-----------------------------------------------
실행:  python tests/test_mp_pose.py

키 조작:
  + / -       임계값  +0.01 / -0.01
  ] / [       연속 프레임 수  +1 / -1
  m           기준점 토글 (코 ↔ 입)
  r           카운터 리셋
  s           현재 설정을 behavior_thread.py 에 저장
  q / ESC     종료

로그:  logs/tune_pose_log.csv  (프레임마다 자동 기록)
"""

import csv
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QImage, QKeySequence, QPainter, QPen, QColor, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

# ── 파라미터 (behavior_thread.py 와 동일하게 시작) ─────────────────────
DIST_THRESHOLD = 0.3
SUCCESS_FRAMES = 4
USE_MOUTH      = False   # False=코(0), True=입 중앙

_NOSE    = 0
_MOUTH_L = 9
_MOUTH_R = 10
_L_WRIST = 15
_R_WRIST = 16

_LOG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "logs", "tune_pose_log.csv")
)
_BEHAVIOR_THREAD_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "ui", "threads", "behavior_thread.py")
)


# ── 포즈 처리 스레드 ────────────────────────────────────────────────────
class PoseThread(QThread):
    frame_ready = pyqtSignal(object, float, float, bool, int)
    # (bgr_frame, dist_l, dist_r, is_near, counter)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def run(self):
        self._running = True
        from camera.camera import get_frame

        pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        counter = 0

        try:
            while self._running:
                frame = get_frame()
                if frame is None:
                    self.msleep(30)
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                dist_l = dist_r = -1.0
                is_near = False

                if results.pose_landmarks:
                    lm = results.pose_landmarks.landmark
                    if USE_MOUTH:
                        rx = (lm[_MOUTH_L].x + lm[_MOUTH_R].x) / 2
                        ry = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
                    else:
                        rx, ry = lm[_NOSE].x, lm[_NOSE].y

                    dist_l = float(np.hypot(lm[_L_WRIST].x - rx, lm[_L_WRIST].y - ry))
                    dist_r = float(np.hypot(lm[_R_WRIST].x - rx, lm[_R_WRIST].y - ry))

                    if min(dist_l, dist_r) < DIST_THRESHOLD:
                        is_near = True

                if is_near:
                    counter += 1
                else:
                    counter = max(0, counter - 1)

                self.frame_ready.emit(frame.copy(), dist_l, dist_r, is_near, counter)
                self.msleep(16)  # ~60fps 상한

        finally:
            pose.close()

    def reset_counter(self):
        pass  # 카운터는 메인 윈도우가 관리

    def stop(self):
        self._running = False


# ── 메인 윈도우 ─────────────────────────────────────────────────────────
class TuneWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("복약행위 감지 튜닝")
        self.resize(800, 520)
        self.setStyleSheet("background: #0f172a;")

        self._counter   = 0
        self._detected  = False
        self._dist_l    = -1.0
        self._dist_r    = -1.0
        self._session_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._frame_no  = 0

        # CSV 준비
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        write_header = not os.path.exists(_LOG_PATH)
        self._log_f = open(_LOG_PATH, "a", newline="", encoding="utf-8")
        self._log_w = csv.writer(self._log_f)
        if write_header:
            self._log_w.writerow([
                "session_time", "frame_no",
                "ref_point", "threshold", "success_frames",
                "dist_left", "dist_right", "min_dist",
                "is_near", "counter", "detected",
            ])

        # 카메라 뷰
        self._cam_lbl = QLabel(self)
        self._cam_lbl.setAlignment(Qt.AlignCenter)
        self._cam_lbl.setMinimumSize(640, 480)

        # HUD 레이블
        self._hud = QLabel(self)
        self._hud.setFont(QFont("Monospace", 13))
        self._hud.setStyleSheet("color: #e2e8f0; background: rgba(0,0,0,160); padding: 8px; border-radius: 6px;")
        self._hud.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        layout.addWidget(self._cam_lbl, stretch=1)
        layout.addWidget(self._hud)

        self._thread = PoseThread(self)
        self._thread.frame_ready.connect(self._on_frame)
        self._thread.start()

        self._update_hud()
        print(f"[LOG] {_LOG_PATH}")
        print("+/-: 임계값  |  ]/[: 프레임수  |  m: 기준점  |  r: 리셋  |  s: 저장  |  q: 종료")

    # ── 프레임 수신 ──────────────────────────────────────────────────────
    def _on_frame(self, frame, dist_l, dist_r, is_near, thread_counter):
        global DIST_THRESHOLD, SUCCESS_FRAMES

        self._dist_l = dist_l
        self._dist_r = dist_r

        # 카운터: thread에서 넘어온 값 사용
        self._counter = thread_counter

        if self._counter >= SUCCESS_FRAMES and not self._detected:
            self._detected = True
            print(f"[DETECTED] TH={DIST_THRESHOLD:.2f}  F={SUCCESS_FRAMES}"
                  f"  L={dist_l:.4f}  R={dist_r:.4f}")

        # CSV 기록
        self._frame_no += 1
        min_d = round(min(dist_l, dist_r), 4) if dist_l >= 0 else -1.0
        self._log_w.writerow([
            self._session_ts, self._frame_no,
            "mouth" if USE_MOUTH else "nose",
            DIST_THRESHOLD, SUCCESS_FRAMES,
            round(dist_l, 4), round(dist_r, 4), min_d,
            1 if is_near else 0, self._counter, 1 if self._detected else 0,
        ])
        self._log_f.flush()

        # 프레임 → QPixmap 변환 후 표시
        h, w = frame.shape[:2]
        qimg = QImage(frame.data, w, h, w * 3, QImage.Format_BGR888)
        pix  = QPixmap.fromImage(qimg).scaled(
            self._cam_lbl.width(), self._cam_lbl.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )

        # 감지 시 초록 테두리
        if self._detected:
            painter = QPainter(pix)
            pen = QPen(QColor(0, 255, 80), 8)
            painter.setPen(pen)
            painter.drawRect(4, 4, pix.width() - 8, pix.height() - 8)
            painter.end()

        self._cam_lbl.setPixmap(pix)
        self._update_hud()

    # ── HUD 업데이트 ─────────────────────────────────────────────────────
    def _update_hud(self):
        ref  = "입(Mouth)" if USE_MOUTH else "코(Nose)"
        l_s  = f"{self._dist_l:.3f}" if self._dist_l >= 0 else "---"
        r_s  = f"{self._dist_r:.3f}" if self._dist_r >= 0 else "---"
        min_s = f"{min(self._dist_l, self._dist_r):.3f}" if self._dist_l >= 0 else "---"
        bar  = "█" * min(self._counter, SUCCESS_FRAMES) + "░" * max(0, SUCCESS_FRAMES - self._counter)
        det  = "  ★ DETECTED!" if self._detected else ""

        lines = [
            f"기준점  : {ref}  [m]",
            f"임계값  : {DIST_THRESHOLD:.2f}  [+ / -]",
            f"프레임수: {SUCCESS_FRAMES}  [] / []",
            f"dist L  : {l_s}   R: {r_s}   min: {min_s}",
            f"counter : {bar}  ({self._counter}/{SUCCESS_FRAMES}){det}",
            f"",
            f"r=리셋  s=behavior_thread.py에저장  q=종료",
        ]
        self._hud.setText("\n".join(lines))

    # ── 키보드 ───────────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        global DIST_THRESHOLD, SUCCESS_FRAMES, USE_MOUTH

        key = event.key()
        if key in (Qt.Key_Q, Qt.Key_Escape):
            self.close()
        elif key == Qt.Key_Plus or key == Qt.Key_Equal:
            DIST_THRESHOLD = round(min(DIST_THRESHOLD + 0.01, 0.99), 2)
            self._reset()
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == Qt.Key_Minus:
            DIST_THRESHOLD = round(max(DIST_THRESHOLD - 0.01, 0.05), 2)
            self._reset()
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == Qt.Key_BracketRight:
            SUCCESS_FRAMES = min(SUCCESS_FRAMES + 1, 30)
            self._reset()
            print(f"[FRAMES] → {SUCCESS_FRAMES}")
        elif key == Qt.Key_BracketLeft:
            SUCCESS_FRAMES = max(SUCCESS_FRAMES - 1, 1)
            self._reset()
            print(f"[FRAMES] → {SUCCESS_FRAMES}")
        elif key == Qt.Key_M:
            USE_MOUTH = not USE_MOUTH
            self._reset()
            print(f"[REF] → {'입(Mouth)' if USE_MOUTH else '코(Nose)'}")
        elif key == Qt.Key_R:
            self._reset()
            print("[RESET]")
        elif key == Qt.Key_S:
            _save_to_behavior_thread(DIST_THRESHOLD, SUCCESS_FRAMES)

    def _reset(self):
        self._counter  = 0
        self._detected = False
        self._update_hud()

    def closeEvent(self, event):
        self._thread.stop()
        self._thread.wait(2000)
        self._log_f.close()
        print(f"\n최종 설정 — 임계값: {DIST_THRESHOLD:.2f}  프레임: {SUCCESS_FRAMES}  기준점: {'입' if USE_MOUTH else '코'}")
        print(f"로그 저장됨: {_LOG_PATH}")
        super().closeEvent(event)


# ── behavior_thread.py 저장 ──────────────────────────────────────────────
def _save_to_behavior_thread(threshold: float, frames: int):
    try:
        with open(_BEHAVIOR_THREAD_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        src = re.sub(r"(_DIST_THRESHOLD\s*=\s*)[\d.]+", lambda m: f"{m.group(1)}{threshold}", src)
        src = re.sub(r"(_SUCCESS_FRAMES\s*=\s*)\d+",   lambda m: f"{m.group(1)}{frames}",    src)
        with open(_BEHAVIOR_THREAD_PATH, "w", encoding="utf-8") as f:
            f.write(src)
        print(f"[SAVED] behavior_thread.py → TH={threshold:.2f}  FRAMES={frames}")
    except Exception as e:
        print(f"[SAVE ERROR] {e}")


# ── 진입점 ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TuneWindow()
    win.show()
    sys.exit(app.exec_())
