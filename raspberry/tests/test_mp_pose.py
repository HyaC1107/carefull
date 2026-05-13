"""
복약행위 감지 파라미터 튜닝 도구  (PyQt5 전체화면 버전)
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
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

# ── 파라미터 ─────────────────────────────────────────────────────────────
DIST_THRESHOLD = 0.3
SUCCESS_FRAMES = 4
USE_MOUTH      = False

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

# 랜드마크 색상
_COL_REF       = (0, 255, 255)    # 기준점 (노란-시안)
_COL_WRIST_HIT = (0, 80, 255)     # 손목 — 임계값 이하 (빨강)
_COL_WRIST_OK  = (180, 255, 80)   # 손목 — 정상 (초록)
_COL_POSE      = (100, 220, 100)  # 나머지 포즈 연결선
_COL_DETECT    = (0, 255, 80)     # 감지 성공 테두리


def _draw_landmarks(frame, results, dist_l, dist_r):
    """포즈 전체 + 기준점/손목 강조 표시."""
    fh, fw = frame.shape[:2]
    lm = results.pose_landmarks.landmark

    # 1) 전체 포즈 스켈레톤
    mp.solutions.drawing_utils.draw_landmarks(
        frame,
        results.pose_landmarks,
        mp.solutions.pose.POSE_CONNECTIONS,
        landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
            color=_COL_POSE, thickness=1, circle_radius=2
        ),
        connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
            color=(80, 180, 80), thickness=1
        ),
    )

    # 2) 기준점 (코 or 입 중앙) — 시안 큰 원
    if USE_MOUTH:
        rx = (lm[_MOUTH_L].x + lm[_MOUTH_R].x) / 2
        ry = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
    else:
        rx, ry = lm[_NOSE].x, lm[_NOSE].y
    ref_px = (int(rx * fw), int(ry * fh))
    cv2.circle(frame, ref_px, 14, _COL_REF, -1)
    cv2.circle(frame, ref_px, 14, (0, 0, 0), 2)

    # 3) 손목 — 거리에 따라 색상 변경
    lw = (int(lm[_L_WRIST].x * fw), int(lm[_L_WRIST].y * fh))
    rw = (int(lm[_R_WRIST].x * fw), int(lm[_R_WRIST].y * fh))
    l_col = _COL_WRIST_HIT if (dist_l >= 0 and dist_l < DIST_THRESHOLD) else _COL_WRIST_OK
    r_col = _COL_WRIST_HIT if (dist_r >= 0 and dist_r < DIST_THRESHOLD) else _COL_WRIST_OK

    cv2.circle(frame, lw, 12, l_col, -1)
    cv2.circle(frame, lw, 12, (0, 0, 0), 2)
    cv2.circle(frame, rw, 12, r_col, -1)
    cv2.circle(frame, rw, 12, (0, 0, 0), 2)

    # 4) 기준점 → 손목 연결선
    cv2.line(frame, ref_px, lw, l_col, 2)
    cv2.line(frame, ref_px, rw, r_col, 2)

    # 5) 거리 숫자를 손목 옆에 표시
    def _label(pt, val, col):
        if val < 0:
            return
        txt = f"{val:.2f}"
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        ox = pt[0] + 16
        oy = pt[1] - 10
        cv2.rectangle(frame, (ox - 2, oy - th - 2), (ox + tw + 2, oy + 4), (0, 0, 0), -1)
        cv2.putText(frame, txt, (ox, oy), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)

    _label(lw, dist_l, l_col)
    _label(rw, dist_r, r_col)


# ── 포즈 처리 스레드 ─────────────────────────────────────────────────────
class PoseThread(QThread):
    frame_ready = pyqtSignal(object, float, float, bool, int)

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

                rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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

                    _draw_landmarks(frame, results, dist_l, dist_r)

                if is_near:
                    counter += 1
                else:
                    counter = max(0, counter - 1)

                self.frame_ready.emit(frame, dist_l, dist_r, is_near, counter)
                self.msleep(16)

        finally:
            pose.close()

    def stop(self):
        self._running = False


# ── 메인 윈도우 (전체화면, HUD 오버레이) ─────────────────────────────────
class TuneWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("복약행위 감지 튜닝")
        self.setStyleSheet("background: black;")

        self._counter    = 0
        self._detected   = False
        self._dist_l     = -1.0
        self._dist_r     = -1.0
        self._session_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._frame_no   = 0
        self._pixmap     = QPixmap()

        # CSV 준비
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        write_header = not os.path.exists(_LOG_PATH)
        self._log_f  = open(_LOG_PATH, "a", newline="", encoding="utf-8")
        self._log_w  = csv.writer(self._log_f)
        if write_header:
            self._log_w.writerow([
                "session_time", "frame_no",
                "ref_point", "threshold", "success_frames",
                "dist_left", "dist_right", "min_dist",
                "is_near", "counter", "detected",
            ])

        self._thread = PoseThread(self)
        self._thread.frame_ready.connect(self._on_frame)
        self._thread.start()

        self.showFullScreen()

        print(f"[LOG] {_LOG_PATH}")
        print("+/-: 임계값  |  ]/[: 프레임수  |  m: 기준점  |  r: 리셋  |  s: 저장  |  q/ESC: 종료")

    # ── 프레임 수신 ──────────────────────────────────────────────────────
    def _on_frame(self, frame, dist_l, dist_r, is_near, thread_counter):
        self._dist_l  = dist_l
        self._dist_r  = dist_r
        self._counter = thread_counter

        if self._counter >= SUCCESS_FRAMES and not self._detected:
            self._detected = True
            print(f"[DETECTED] TH={DIST_THRESHOLD:.2f}  F={SUCCESS_FRAMES}"
                  f"  L={dist_l:.4f}  R={dist_r:.4f}")

        # CSV 로그
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

        h, w = frame.shape[:2]
        qimg = QImage(frame.data, w, h, w * 3, QImage.Format_BGR888)
        self._pixmap = QPixmap.fromImage(qimg)
        self.update()   # paintEvent 호출

    # ── 전체화면 렌더링 ──────────────────────────────────────────────────
    def paintEvent(self, event):
        if self._pixmap.isNull():
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        sw, sh = self.width(), self.height()

        # 카메라 프레임 — 화면에 꽉 채우기 (비율 유지)
        scaled = self._pixmap.scaled(sw, sh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ox = (sw - scaled.width())  // 2
        oy = (sh - scaled.height()) // 2
        p.drawPixmap(ox, oy, scaled)

        # 감지 성공 — 초록 테두리
        if self._detected:
            pen = QPen(QColor(0, 255, 80), 10)
            p.setPen(pen)
            p.drawRect(5, 5, sw - 10, sh - 10)

        # ── HUD 오버레이 (좌상단) ─────────────────────────────────────
        p.setFont(QFont("Monospace", 15, QFont.Bold))

        def draw_line(text, y, color=Qt.white):
            fm   = p.fontMetrics()
            tw   = fm.horizontalAdvance(text)
            th   = fm.height()
            # 배경 박스
            p.fillRect(10, y - th + 4, tw + 16, th + 4, QColor(0, 0, 0, 160))
            p.setPen(QColor(color) if isinstance(color, str) else color)
            p.drawText(18, y + 2, text)

        ref_lbl = "입(Mouth)" if USE_MOUTH else "코(Nose )"
        l_s = f"{self._dist_l:.3f}" if self._dist_l >= 0 else " --- "
        r_s = f"{self._dist_r:.3f}" if self._dist_r >= 0 else " --- "
        min_d = min(self._dist_l, self._dist_r) if self._dist_l >= 0 else -1.0
        min_s = f"{min_d:.3f}" if min_d >= 0 else " --- "

        bar_fill = "█" * min(self._counter, SUCCESS_FRAMES)
        bar_empty = "░" * max(0, SUCCESS_FRAMES - self._counter)
        det_str = "  ★ DETECTED!" if self._detected else ""

        th_color  = QColor(100, 255, 100)
        frm_color = QColor(100, 200, 255)
        hit_color = QColor(80, 160, 255)
        white     = QColor(230, 230, 230)

        y = 36
        step = 32
        draw_line(f"기준점   : {ref_lbl}              [m]",           y,        QColor(255, 240, 100))
        draw_line(f"임계값   : {DIST_THRESHOLD:.2f}                   [+ / -]", y+step,   th_color)
        draw_line(f"연속프레임: {SUCCESS_FRAMES}                       [] / []", y+step*2, frm_color)
        draw_line(f"dist L: {l_s}   R: {r_s}   min: {min_s}",                  y+step*3, hit_color)
        draw_line(f"counter: {bar_fill}{bar_empty} ({self._counter}/{SUCCESS_FRAMES}){det_str}",
                  y+step*4, QColor(0, 255, 80) if self._detected else white)

        # 우하단 — 조작 안내
        p.setFont(QFont("Monospace", 12))
        hint = "r=리셋  s=저장  q=종료"
        fw2  = p.fontMetrics().horizontalAdvance(hint)
        fh2  = p.fontMetrics().height()
        p.fillRect(sw - fw2 - 24, sh - fh2 - 14, fw2 + 16, fh2 + 8, QColor(0, 0, 0, 160))
        p.setPen(QColor(160, 160, 160))
        p.drawText(sw - fw2 - 16, sh - 12, hint)

        p.end()

    # ── 키보드 ───────────────────────────────────────────────────────────
    def keyPressEvent(self, event):
        global DIST_THRESHOLD, SUCCESS_FRAMES, USE_MOUTH

        key = event.key()
        if key in (Qt.Key_Q, Qt.Key_Escape):
            self.close()
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            DIST_THRESHOLD = round(min(DIST_THRESHOLD + 0.01, 0.99), 2)
            self._reset(); print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == Qt.Key_Minus:
            DIST_THRESHOLD = round(max(DIST_THRESHOLD - 0.01, 0.05), 2)
            self._reset(); print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == Qt.Key_BracketRight:
            SUCCESS_FRAMES = min(SUCCESS_FRAMES + 1, 30)
            self._reset(); print(f"[FRAMES] → {SUCCESS_FRAMES}")
        elif key == Qt.Key_BracketLeft:
            SUCCESS_FRAMES = max(SUCCESS_FRAMES - 1, 1)
            self._reset(); print(f"[FRAMES] → {SUCCESS_FRAMES}")
        elif key == Qt.Key_M:
            USE_MOUTH = not USE_MOUTH
            self._reset(); print(f"[REF] → {'입(Mouth)' if USE_MOUTH else '코(Nose)'}")
        elif key == Qt.Key_R:
            self._reset(); print("[RESET]")
        elif key == Qt.Key_S:
            _save_to_behavior_thread(DIST_THRESHOLD, SUCCESS_FRAMES)

    def _reset(self):
        self._counter  = 0
        self._detected = False
        self.update()

    def closeEvent(self, event):
        self._thread.stop()
        self._thread.wait(2000)
        self._log_f.close()
        print(f"\n최종 — TH: {DIST_THRESHOLD:.2f}  FRAMES: {SUCCESS_FRAMES}"
              f"  기준점: {'입' if USE_MOUTH else '코'}")
        print(f"로그: {_LOG_PATH}")
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TuneWindow()
    sys.exit(app.exec_())
