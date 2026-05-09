#!/usr/bin/env python3
"""
비교 테스트: MediaPipe Pose 단독
판단 로직: 코(0) ↔ 왼손목(15) / 오른손목(16) 중 가까운 쪽 거리
카메라: Raspberry Pi Camera Module 3 (Picamera2, RGB888)

실행 방법 (SSH):
  export DISPLAY=:0
  python test_mp_pose.py

키 조작 (SSH 터미널):
  1 — 트라이얼 시작
  2 — 트라이얼 중지
  3 — 종료
"""

import csv
import logging
import os
import select
import sys
import termios
import tty
import time
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np
from picamera2 import Picamera2


# ── 설정 ─────────────────────────────────────────────────────────────
INTAKE_DISTANCE_THRESHOLD = 0.5
SUCCESS_REQUIRED_FRAMES = 4

CAM_W = 1280
CAM_H = 720

_WIN = "MP Pose | Intake Detection"

NOSE = 0
L_WRIST = 15
R_WRIST = 16


# ── 터미널 non-blocking 입력 ────────────────────────────────────────
class _TermInput:
    def __init__(self):
        self._fd = sys.stdin.fileno()
        self._old = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)

    def read(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return os.read(self._fd, 1).decode("utf-8", errors="ignore")
        return None

    def restore(self):
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)


# ── 로깅 설정 ───────────────────────────────────────────────────────
_MODEL = "mp_pose"

_LOG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "logs"
)

os.makedirs(_LOG_DIR, exist_ok=True)

_TAG = datetime.now().strftime("%Y%m%d_%H%M%S")

_LOG_FILE = os.path.join(
    _LOG_DIR,
    f"{_TAG}_{_MODEL}.log"
)

_CSV_FILE = os.path.join(
    _LOG_DIR,
    "summary.csv"
)

_log = logging.getLogger(_MODEL)
_log.setLevel(logging.DEBUG)

_fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_fh.setFormatter(
    logging.Formatter(
        "%(asctime)s  %(message)s",
        datefmt="%H:%M:%S"
    )
)

_log.addHandler(_fh)

_ch = logging.StreamHandler()
_ch.setFormatter(
    logging.Formatter(
        "%(asctime)s  %(message)s",
        datefmt="%H:%M:%S"
    )
)

_log.addHandler(_ch)


# ── MediaPipe 초기화 ────────────────────────────────────────────────
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)


# ── 카메라 초기화 ───────────────────────────────────────────────────
picam2 = Picamera2()

picam2.configure(
    picam2.create_preview_configuration(
        main={
            "format": "RGB888",
            "size": (CAM_W, CAM_H)
        }
    )
)

picam2.start()


# ── 상태 변수 ───────────────────────────────────────────────────────
STATE_IDLE = "IDLE"
STATE_ACTIVE = "ACTIVE"

intake_counter = 0
total_frames = 0
near_frames = 0

prev_time = time.time()

_state = STATE_IDLE
_trial_no = 0
_trial_t = None
_approach_t = None
_fired = False
_prev_cnt = 0
_trials = []

_t0 = time.time()
_fps_list = []


# ── 로그 시작 ───────────────────────────────────────────────────────
_log.info("=" * 60)
_log.info("세션 시작  모델=%s", _MODEL)
_log.info(
    "threshold=%.2f  success_frames=%d",
    INTAKE_DISTANCE_THRESHOLD,
    SUCCESS_REQUIRED_FRAMES
)
_log.info("해상도=%dx%d", CAM_W, CAM_H)
_log.info("조작: 1=시작  2=중지  3=종료")
_log.info("로그파일=%s", _LOG_FILE)
_log.info("=" * 60)

print(f"\n[{_MODEL}] 준비 완료")
print("SSH 터미널: 1=시작  2=중지  3=종료")
print(f"로그: {_LOG_FILE}\n")


# ── 입력 초기화 ─────────────────────────────────────────────────────
_term = _TermInput()


# ── 전체화면 설정 ───────────────────────────────────────────────────
cv2.namedWindow(_WIN, cv2.WINDOW_NORMAL)

cv2.setWindowProperty(
    _WIN,
    cv2.WND_PROP_FULLSCREEN,
    cv2.WINDOW_FULLSCREEN
)

cv2.resizeWindow(_WIN, CAM_W, CAM_H)


# ── 메인 루프 ───────────────────────────────────────────────────────
try:
    fps = 0.0

    while True:

        # ── 카메라 프레임 ─────────────────────────────────────────
        frame = picam2.capture_array()

        # 상하 + 좌우 반전
        frame = cv2.flip(frame, -1)

        total_frames += 1

        h, w = frame.shape[:2]

        # MediaPipe 처리용 RGB
        results = pose.process(frame)

        # OpenCV 출력용 BGR 변환
        disp = frame

        is_near = False
        current_dist = 1.0
        closer_pt = None

        # ── 랜드마크 처리 ────────────────────────────────────────
        if results.pose_landmarks:

            lm = results.pose_landmarks.landmark

            mp_draw.draw_landmarks(
                disp,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                mp_draw.DrawingSpec(
                    color=(0, 255, 0),
                    thickness=2,
                    circle_radius=3
                ),
                mp_draw.DrawingSpec(
                    color=(0, 200, 0),
                    thickness=2
                ),
            )

            nose = lm[NOSE]
            l_wrist = lm[L_WRIST]
            r_wrist = lm[R_WRIST]

            nose_pt = (
                int(nose.x * w),
                int(nose.y * h)
            )

            lw_pt = (
                int(l_wrist.x * w),
                int(l_wrist.y * h)
            )

            rw_pt = (
                int(r_wrist.x * w),
                int(r_wrist.y * h)
            )

            cv2.circle(disp, nose_pt, 8, (255, 255, 0), -1)
            cv2.circle(disp, lw_pt, 8, (0, 255, 255), -1)
            cv2.circle(disp, rw_pt, 8, (0, 255, 255), -1)

            dist_l = float(
                np.hypot(
                    l_wrist.x - nose.x,
                    l_wrist.y - nose.y
                )
            )

            dist_r = float(
                np.hypot(
                    r_wrist.x - nose.x,
                    r_wrist.y - nose.y
                )
            )

            if dist_l < dist_r:
                current_dist = dist_l
                closer_pt = lw_pt
            else:
                current_dist = dist_r
                closer_pt = rw_pt

            if current_dist < INTAKE_DISTANCE_THRESHOLD:
                is_near = True

                cv2.line(
                    disp,
                    nose_pt,
                    closer_pt,
                    (0, 255, 0),
                    3
                )

        # ── 감지 로직 ───────────────────────────────────────────
        if _state == STATE_ACTIVE:

            if results.pose_landmarks:
                if current_dist < INTAKE_DISTANCE_THRESHOLD:
                    intake_counter += 1
                else:
                    intake_counter = max(0, intake_counter - 1)
            else:
                intake_counter = max(0, intake_counter - 1)

            if is_near:
                near_frames += 1

            if intake_counter >= 1 and _prev_cnt == 0:
                _approach_t = time.time()
                _fired = False

                _log.info(
                    "접근 시작 frame=%d dist=%.4f",
                    total_frames,
                    current_dist
                )

            if intake_counter >= SUCCESS_REQUIRED_FRAMES and not _fired:

                _fired = True

                approach_dur = (
                    time.time() - _approach_t
                    if _approach_t else 0
                )

                trial_dur = time.time() - _trial_t

                _log.info(
                    "*** 복약감지 *** dist=%.4f 접근→감지=%.2fs fps=%.1f",
                    current_dist,
                    approach_dur,
                    fps
                )

                _trials.append({
                    "no": _trial_no,
                    "detected": True,
                    "duration_s": round(trial_dur, 2),
                    "approach_s": round(approach_dur, 2),
                    "detect_dist": round(current_dist, 4),
                })

                intake_counter = 0
                _state = STATE_IDLE

            _prev_cnt = intake_counter

        # ── FPS 계산 ────────────────────────────────────────────
        curr_time = time.time()

        fps = 1.0 / max(curr_time - prev_time, 1e-9)

        prev_time = curr_time

        _fps_list.append(fps)

        # ── 키 입력 ─────────────────────────────────────────────
        key = _term.read()

        if key == '1' and _state == STATE_IDLE:

            intake_counter = 0
            _prev_cnt = 0
            _approach_t = None
            _fired = False

            _trial_no += 1
            _trial_t = time.time()

            _state = STATE_ACTIVE

            _log.info("Trial #%d 시작", _trial_no)

        elif key == '2' and _state == STATE_ACTIVE:

            trial_dur = time.time() - _trial_t

            _log.info(
                "Trial #%d 중지 (미감지) 소요=%.2fs",
                _trial_no,
                trial_dur
            )

            _trials.append({
                "no": _trial_no,
                "detected": False,
                "duration_s": round(trial_dur, 2),
                "approach_s": None,
                "detect_dist": None,
            })

            intake_counter = 0
            _state = STATE_IDLE

        elif key == '3':
            break

        # ── UI 표시 ────────────────────────────────────────────
        detected_cnt = sum(
            1 for t in _trials if t["detected"]
        )

        color = (
            (0, 255, 0)
            if is_near else
            (0, 0, 255)
        )

        cv2.putText(
            disp,
            f"FPS: {fps:.1f}",
            (w - 180, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2
        )

        cv2.putText(
            disp,
            f"Dist: {current_dist:.4f}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            color,
            2
        )

        if _state == STATE_ACTIVE:
            cv2.putText(
                disp,
                f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}",
                (20, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                color,
                2
            )

        cv2.imshow(_WIN, disp)

        cv2.waitKey(1)

finally:

    _term.restore()

    cv2.destroyAllWindows()

    picam2.stop()

    pose.close()

    print("\n종료 완료")