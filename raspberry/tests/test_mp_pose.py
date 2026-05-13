"""
Behavior detection tuning tool
- Full-screen camera display on Pi display
- SSH keyboard input via QSocketNotifier (stdin)

Keys:
  + / -   threshold +/- 0.01
  ] / [   success frames +/- 1
  v / V   visibility threshold +/- 0.05
  m       toggle reference point (nose / mouth)
  r       reset counter
  s       save to behavior_thread.py
  q/ESC   quit
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
from PyQt5.QtCore import Qt, QThread, QSocketNotifier, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget

# ── parameters ───────────────────────────────────────────────────────────
DIST_THRESHOLD = 0.3
SUCCESS_FRAMES = 4
USE_MOUTH      = False
VIS_THRESHOLD  = 0.5

_NOSE    = 0
_MOUTH_L = 9
_MOUTH_R = 10
_L_WRIST = 15
_R_WRIST = 16

_LOG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "logs", "tune_pose_log.csv")
)
_BEHAVIOR_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "ui", "threads", "behavior_thread.py")
)

# landmark colors (BGR for OpenCV drawing)
_COL_REF      = (0, 255, 255)   # cyan  — reference point
_COL_WRIST_HI = (0, 80, 255)    # red   — wrist within threshold
_COL_WRIST_OK = (80, 255, 100)  # green — wrist normal
_COL_SKEL     = (80, 200, 80)   # green — skeleton


def _draw_on_frame(frame, results, dist_l, dist_r):
    """Draw full skeleton + highlighted reference/wrist landmarks."""
    fh, fw = frame.shape[:2]
    lm = results.pose_landmarks.landmark

    # full skeleton
    mp.solutions.drawing_utils.draw_landmarks(
        frame,
        results.pose_landmarks,
        mp.solutions.pose.POSE_CONNECTIONS,
        landmark_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
            color=_COL_SKEL, thickness=1, circle_radius=2
        ),
        connection_drawing_spec=mp.solutions.drawing_utils.DrawingSpec(
            color=(60, 160, 60), thickness=1
        ),
    )

    # reference point
    if USE_MOUTH:
        rx = (lm[_MOUTH_L].x + lm[_MOUTH_R].x) / 2
        ry = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
    else:
        rx, ry = lm[_NOSE].x, lm[_NOSE].y
    ref_px = (int(rx * fw), int(ry * fh))
    cv2.circle(frame, ref_px, 14, _COL_REF, -1)
    cv2.circle(frame, ref_px, 14, (0, 0, 0), 2)

    # wrists
    lw = (int(lm[_L_WRIST].x * fw), int(lm[_L_WRIST].y * fh))
    rw = (int(lm[_R_WRIST].x * fw), int(lm[_R_WRIST].y * fh))
    lc = _COL_WRIST_HI if (0 <= dist_l < DIST_THRESHOLD) else _COL_WRIST_OK
    rc = _COL_WRIST_HI if (0 <= dist_r < DIST_THRESHOLD) else _COL_WRIST_OK

    for pt, col in [(lw, lc), (rw, rc)]:
        cv2.circle(frame, pt, 12, col, -1)
        cv2.circle(frame, pt, 12, (0, 0, 0), 2)

    # lines ref → wrist
    cv2.line(frame, ref_px, lw, lc, 2)
    cv2.line(frame, ref_px, rw, rc, 2)

    # distance labels next to wrists
    for pt, val, col in [(lw, dist_l, lc), (rw, dist_r, rc)]:
        if val < 0:
            continue
        txt = f"{val:.2f}"
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        ox, oy = pt[0] + 16, pt[1] - 8
        cv2.rectangle(frame, (ox - 2, oy - th - 2), (ox + tw + 2, oy + 4), (0, 0, 0), -1)
        cv2.putText(frame, txt, (ox, oy), cv2.FONT_HERSHEY_SIMPLEX, 0.65, col, 2)


# ── pose thread ───────────────────────────────────────────────────────────
class PoseThread(QThread):
    frame_ready = pyqtSignal(object, float, float, float, float, float, bool, int)
    # frame, dist_l, dist_r, vis_nose, vis_lw, vis_rw, is_near, counter

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._counter = 0

    def reset(self):
        self._counter = 0

    def run(self):
        self._running = True
        from camera.camera import get_frame

        pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        try:
            while self._running:
                frame = get_frame()
                if frame is None:
                    self.msleep(30)
                    continue

                rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = pose.process(rgb)

                dist_l = dist_r = -1.0
                vis_nose = vis_lw = vis_rw = -1.0
                is_near = False

                if results.pose_landmarks:
                    lm = results.pose_landmarks.landmark
                    vis_nose = float(lm[_NOSE].visibility)
                    vis_lw   = float(lm[_L_WRIST].visibility)
                    vis_rw   = float(lm[_R_WRIST].visibility)

                    ref_ok = vis_nose >= VIS_THRESHOLD
                    lw_ok  = vis_lw   >= VIS_THRESHOLD
                    rw_ok  = vis_rw   >= VIS_THRESHOLD

                    if USE_MOUTH:
                        ref_ok = (
                            lm[_MOUTH_L].visibility >= VIS_THRESHOLD and
                            lm[_MOUTH_R].visibility >= VIS_THRESHOLD
                        )

                    if ref_ok:
                        if USE_MOUTH:
                            rx = (lm[_MOUTH_L].x + lm[_MOUTH_R].x) / 2
                            ry = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
                        else:
                            rx, ry = lm[_NOSE].x, lm[_NOSE].y

                        if lw_ok:
                            dist_l = float(np.hypot(lm[_L_WRIST].x - rx, lm[_L_WRIST].y - ry))
                        if rw_ok:
                            dist_r = float(np.hypot(lm[_R_WRIST].x - rx, lm[_R_WRIST].y - ry))

                        valid = [d for d in [dist_l, dist_r] if d >= 0]
                        if valid and min(valid) < DIST_THRESHOLD:
                            is_near = True

                    _draw_on_frame(frame, results, dist_l, dist_r)

                if is_near:
                    self._counter += 1
                else:
                    self._counter = max(0, self._counter - 1)

                self.frame_ready.emit(
                    frame, dist_l, dist_r,
                    vis_nose, vis_lw, vis_rw,
                    is_near, self._counter,
                )
                self.msleep(16)

        finally:
            pose.close()

    def stop(self):
        self._running = False


# ── main window ───────────────────────────────────────────────────────────
class TuneWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Behavior Tuning")
        self.setStyleSheet("background: black;")

        self._detected   = False
        self._dist_l     = -1.0
        self._dist_r     = -1.0
        self._vis_nose   = -1.0
        self._vis_lw     = -1.0
        self._vis_rw     = -1.0
        self._counter    = 0
        self._frame_no   = 0
        self._session_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._pixmap     = QPixmap()

        # CSV log
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        write_header = not os.path.exists(_LOG_PATH)
        self._log_f  = open(_LOG_PATH, "a", newline="", encoding="utf-8")
        self._log_w  = csv.writer(self._log_f)
        if write_header:
            self._log_w.writerow([
                "session_time", "frame_no",
                "ref_point", "threshold", "success_frames", "vis_threshold",
                "dist_left", "dist_right", "min_dist",
                "is_near", "counter", "detected",
            ])

        # pose thread
        self._thread = PoseThread(self)
        self._thread.frame_ready.connect(self._on_frame)
        self._thread.start()

        # SSH keyboard: QSocketNotifier reads from stdin
        self._notifier = QSocketNotifier(sys.stdin.fileno(), QSocketNotifier.Read, self)
        self._notifier.activated.connect(self._on_stdin)

        self.showFullScreen()
        print(f"Log: {_LOG_PATH}")
        print("Keys: +/- threshold  ]/[ frames  v/V visibility  m ref  r reset  s save  q quit")

    # ── frame received ───────────────────────────────────────────────────
    def _on_frame(self, frame, dist_l, dist_r, vis_nose, vis_lw, vis_rw, is_near, counter):
        global DIST_THRESHOLD, SUCCESS_FRAMES

        self._dist_l   = dist_l
        self._dist_r   = dist_r
        self._vis_nose = vis_nose
        self._vis_lw   = vis_lw
        self._vis_rw   = vis_rw
        self._counter  = counter

        if counter >= SUCCESS_FRAMES and not self._detected:
            self._detected = True
            print(f"[DETECTED] TH={DIST_THRESHOLD:.2f} F={SUCCESS_FRAMES} "
                  f"L={dist_l:.4f} R={dist_r:.4f}")

        # CSV
        self._frame_no += 1
        valid = [d for d in [dist_l, dist_r] if d >= 0]
        min_d = round(min(valid), 4) if valid else -1.0
        self._log_w.writerow([
            self._session_ts, self._frame_no,
            "mouth" if USE_MOUTH else "nose",
            DIST_THRESHOLD, SUCCESS_FRAMES, VIS_THRESHOLD,
            round(dist_l, 4), round(dist_r, 4), min_d,
            1 if is_near else 0, counter, 1 if self._detected else 0,
        ])
        self._log_f.flush()

        # BGR → RGB for Qt
        h, w  = frame.shape[:2]
        
        qimg  = QImage(frame.data, w, h, w * 3, QImage.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qimg.copy())
        self.update()

    # ── paint ────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        if self._pixmap.isNull():
            return

        p  = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        sw, sh = self.width(), self.height()

        # camera frame (aspect-ratio preserved, centered)
        scaled = self._pixmap.scaled(sw, sh, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        ox = (sw - scaled.width())  // 2
        oy = (sh - scaled.height()) // 2
        p.drawPixmap(ox, oy, scaled)

        # detected border
        if self._detected:
            p.setPen(QPen(QColor(0, 255, 80), 10))
            p.drawRect(5, 5, sw - 10, sh - 10)

        # HUD overlay
        p.setFont(QFont("Monospace", 14, QFont.Bold))

        def hud_line(text, y, color=QColor(230, 230, 230)):
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(text)
            th = fm.height()
            p.fillRect(10, y - th + 2, tw + 16, th + 6, QColor(0, 0, 0, 170))
            p.setPen(color)
            p.drawText(18, y + 4, text)

        def vis_col(v):
            if v < 0:
                return QColor(120, 120, 120)
            return QColor(80, 220, 80) if v >= VIS_THRESHOLD else QColor(220, 80, 80)

        def dist_col(d):
            if d < 0:
                return QColor(120, 120, 120)
            return QColor(220, 80, 80) if d < DIST_THRESHOLD else QColor(80, 220, 80)

        ref_lbl = "mouth" if USE_MOUTH else "nose "
        vis_n_s = f"{self._vis_nose:.2f}" if self._vis_nose >= 0 else "---"
        vis_l_s = f"{self._vis_lw:.2f}"   if self._vis_lw   >= 0 else "---"
        vis_r_s = f"{self._vis_rw:.2f}"   if self._vis_rw   >= 0 else "---"
        d_l_s   = f"{self._dist_l:.3f}"   if self._dist_l   >= 0 else "---"
        d_r_s   = f"{self._dist_r:.3f}"   if self._dist_r   >= 0 else "---"

        bar = "#" * min(self._counter, SUCCESS_FRAMES) + \
              "." * max(0, SUCCESS_FRAMES - self._counter)
        det = "  *** DETECTED ***" if self._detected else ""

        step = 30
        y    = 32
        hud_line(f"ref:{ref_lbl}  TH:{DIST_THRESHOLD:.2f}  frames:{SUCCESS_FRAMES}  vis:{VIS_THRESHOLD:.2f}", y, QColor(255, 220, 60))
        hud_line(f"vis  nose:{vis_n_s}  L:{vis_l_s}  R:{vis_r_s}", y + step, QColor(180, 220, 255))
        hud_line(f"dist L:{d_l_s}  R:{d_r_s}", y + step * 2,
                 dist_col(min(d for d in [self._dist_l, self._dist_r] if d >= 0) if any(d >= 0 for d in [self._dist_l, self._dist_r]) else -1))
        hud_line(f"[{bar}] {self._counter}/{SUCCESS_FRAMES}{det}", y + step * 3,
                 QColor(0, 255, 80) if self._detected else QColor(100, 180, 255))

        # bottom-right hint
        p.setFont(QFont("Monospace", 11))
        hint = "+/-:TH  ]/[:frames  v/V:vis  m:ref  r:reset  s:save  q:quit"
        fw2  = p.fontMetrics().horizontalAdvance(hint)
        fh2  = p.fontMetrics().height()
        p.fillRect(sw - fw2 - 20, sh - fh2 - 12, fw2 + 12, fh2 + 8, QColor(0, 0, 0, 160))
        p.setPen(QColor(150, 150, 150))
        p.drawText(sw - fw2 - 14, sh - 10, hint)

        p.end()

    # ── Qt keyboard (when window has focus on Pi display) ────────────────
    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key_Q, Qt.Key_Escape):
            self.close()
        elif key in (Qt.Key_Plus, Qt.Key_Equal):
            self._adjust_th(+0.01)
        elif key == Qt.Key_Minus:
            self._adjust_th(-0.01)
        elif key == Qt.Key_BracketRight:
            self._adjust_frames(+1)
        elif key == Qt.Key_BracketLeft:
            self._adjust_frames(-1)
        elif key == Qt.Key_V:
            delta = -0.05 if event.modifiers() & Qt.ShiftModifier else +0.05
            self._adjust_vis(delta)
        elif key == Qt.Key_M:
            self._toggle_mouth()
        elif key == Qt.Key_R:
            self._reset()
        elif key == Qt.Key_S:
            self._save()

    # ── SSH keyboard (stdin via QSocketNotifier) ─────────────────────────
    def _on_stdin(self):
        ch = sys.stdin.read(1)
        if ch in ('q', 'Q'):
            self.close()
        elif ch in ('+', '='):
            self._adjust_th(+0.01)
        elif ch == '-':
            self._adjust_th(-0.01)
        elif ch == ']':
            self._adjust_frames(+1)
        elif ch == '[':
            self._adjust_frames(-1)
        elif ch == 'v':
            self._adjust_vis(+0.05)
        elif ch == 'V':
            self._adjust_vis(-0.05)
        elif ch == 'm':
            self._toggle_mouth()
        elif ch == 'r':
            self._reset()
        elif ch == 's':
            self._save()

    # ── parameter helpers ─────────────────────────────────────────────────
    def _adjust_th(self, delta):
        global DIST_THRESHOLD
        DIST_THRESHOLD = round(max(0.05, min(0.99, DIST_THRESHOLD + delta)), 2)
        self._reset()
        print(f"[TH] {DIST_THRESHOLD:.2f}")

    def _adjust_frames(self, delta):
        global SUCCESS_FRAMES
        SUCCESS_FRAMES = max(1, min(30, SUCCESS_FRAMES + delta))
        self._reset()
        print(f"[FRAMES] {SUCCESS_FRAMES}")

    def _adjust_vis(self, delta):
        global VIS_THRESHOLD
        VIS_THRESHOLD = round(max(0.0, min(1.0, VIS_THRESHOLD + delta)), 2)
        self._reset()
        print(f"[VIS] {VIS_THRESHOLD:.2f}")

    def _toggle_mouth(self):
        global USE_MOUTH
        USE_MOUTH = not USE_MOUTH
        self._reset()
        print(f"[REF] {'mouth' if USE_MOUTH else 'nose'}")

    def _reset(self):
        self._detected = False
        self._thread.reset()

    def _save(self):
        try:
            with open(_BEHAVIOR_PATH, "r", encoding="utf-8") as f:
                src = f.read()
            src = re.sub(
                r"(_DIST_THRESHOLD\s*=\s*)[\d.]+",
                lambda m: f"{m.group(1)}{DIST_THRESHOLD}", src,
            )
            src = re.sub(
                r"(_SUCCESS_FRAMES\s*=\s*)\d+",
                lambda m: f"{m.group(1)}{SUCCESS_FRAMES}", src,
            )
            with open(_BEHAVIOR_PATH, "w", encoding="utf-8") as f:
                f.write(src)
            print(f"[SAVED] TH={DIST_THRESHOLD:.2f}  FRAMES={SUCCESS_FRAMES}")
        except Exception as e:
            print(f"[SAVE ERROR] {e}")

    def closeEvent(self, event):
        self._notifier.setEnabled(False)
        self._thread.stop()
        self._thread.wait(2000)
        self._log_f.close()
        print(f"Final: TH={DIST_THRESHOLD:.2f}  FRAMES={SUCCESS_FRAMES}  "
              f"VIS={VIS_THRESHOLD:.2f}  ref={'mouth' if USE_MOUTH else 'nose'}")
        print(f"Log: {_LOG_PATH}")
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TuneWindow()
    sys.exit(app.exec_())
