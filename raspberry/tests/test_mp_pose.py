"""
복약행위 감지 파라미터 튜닝 도구 (SSH 터미널 버전)
--------------------------------------------------
실행:  python tests/test_mp_pose.py

키 조작 (SSH 터미널에서 바로 입력):
  + / =       임계값 +0.01
  -           임계값 -0.01
  ]           연속 프레임 수 +1
  [           연속 프레임 수 -1
  v           visibility 임계값 +0.05 (오감지 줄이기)
  V           visibility 임계값 -0.05
  m           기준점 토글 (코 ↔ 입)
  r           카운터 리셋
  s           현재 설정을 behavior_thread.py 에 저장
  q           종료

로그:  logs/tune_pose_log.csv
"""

import csv
import datetime
import os
import re
import select
import sys
import termios
import threading
import time
import tty

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import mediapipe as mp
import numpy as np

# ── 파라미터 ─────────────────────────────────────────────────────────────
DIST_THRESHOLD  = 0.3
SUCCESS_FRAMES  = 4
USE_MOUTH       = False
VIS_THRESHOLD   = 0.5   # 랜드마크 visibility 최소값 (낮으면 오감지 필터)

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

# ── ANSI 색상 ─────────────────────────────────────────────────────────────
_R  = "\033[91m"   # 빨강
_G  = "\033[92m"   # 초록
_Y  = "\033[93m"   # 노랑
_B  = "\033[94m"   # 파랑
_C  = "\033[96m"   # 시안
_W  = "\033[97m"   # 흰색
_DIM = "\033[2m"
_RST = "\033[0m"
_CLR = "\033[2J\033[H"   # 화면 클리어 + 커서 홈


# ── 공유 상태 ─────────────────────────────────────────────────────────────
_state = {
    "dist_l":    -1.0,
    "dist_r":    -1.0,
    "vis_nose":  -1.0,
    "vis_lw":    -1.0,
    "vis_rw":    -1.0,
    "is_near":   False,
    "counter":   0,
    "detected":  False,
    "landmarks_ok": False,
    "frame_no":  0,
    "running":   True,
}
_lock = threading.Lock()


# ── 카메라 + 포즈 처리 스레드 ─────────────────────────────────────────────
def _pose_worker(log_writer, log_file):
    from camera.camera import get_frame

    pose = mp.solutions.pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    session_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counter = 0

    try:
        while _state["running"]:
            frame = get_frame()
            if frame is None:
                time.sleep(0.03)
                continue

            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)

            dist_l = dist_r = -1.0
            vis_nose = vis_lw = vis_rw = -1.0
            is_near = False
            landmarks_ok = False

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark

                vis_nose = lm[_NOSE].visibility
                vis_lw   = lm[_L_WRIST].visibility
                vis_rw   = lm[_R_WRIST].visibility

                # visibility 통과한 랜드마크만 사용
                ref_ok = vis_nose >= VIS_THRESHOLD
                lw_ok  = vis_lw   >= VIS_THRESHOLD
                rw_ok  = vis_rw   >= VIS_THRESHOLD

                if USE_MOUTH:
                    vis_ml = lm[_MOUTH_L].visibility
                    vis_mr = lm[_MOUTH_R].visibility
                    ref_ok = (vis_ml >= VIS_THRESHOLD and vis_mr >= VIS_THRESHOLD)

                if ref_ok:
                    landmarks_ok = True
                    if USE_MOUTH:
                        rx = (lm[_MOUTH_L].x + lm[_MOUTH_R].x) / 2
                        ry = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
                    else:
                        rx, ry = lm[_NOSE].x, lm[_NOSE].y

                    if lw_ok:
                        dist_l = float(np.hypot(lm[_L_WRIST].x - rx, lm[_L_WRIST].y - ry))
                    if rw_ok:
                        dist_r = float(np.hypot(lm[_R_WRIST].x - rx, lm[_R_WRIST].y - ry))

                    valid_dists = [d for d in [dist_l, dist_r] if d >= 0]
                    if valid_dists and min(valid_dists) < DIST_THRESHOLD:
                        is_near = True

            if is_near:
                counter += 1
            else:
                counter = max(0, counter - 1)

            with _lock:
                _state["dist_l"]       = dist_l
                _state["dist_r"]       = dist_r
                _state["vis_nose"]     = vis_nose
                _state["vis_lw"]       = vis_lw
                _state["vis_rw"]       = vis_rw
                _state["is_near"]      = is_near
                _state["counter"]      = counter
                _state["landmarks_ok"] = landmarks_ok
                _state["frame_no"]    += 1
                fn = _state["frame_no"]

                if counter >= SUCCESS_FRAMES and not _state["detected"]:
                    _state["detected"] = True

                detected = _state["detected"]

            # CSV 로그
            min_d = round(min(d for d in [dist_l, dist_r] if d >= 0), 4) if any(d >= 0 for d in [dist_l, dist_r]) else -1.0
            log_writer.writerow([
                session_ts, fn,
                "mouth" if USE_MOUTH else "nose",
                DIST_THRESHOLD, SUCCESS_FRAMES, VIS_THRESHOLD,
                round(dist_l, 4), round(dist_r, 4), min_d,
                1 if is_near else 0, counter, 1 if detected else 0,
            ])
            log_file.flush()

    finally:
        pose.close()


# ── 화면 출력 ─────────────────────────────────────────────────────────────
def _render():
    with _lock:
        dist_l      = _state["dist_l"]
        dist_r      = _state["dist_r"]
        vis_nose    = _state["vis_nose"]
        vis_lw      = _state["vis_lw"]
        vis_rw      = _state["vis_rw"]
        counter     = _state["counter"]
        detected    = _state["detected"]
        landmarks_ok = _state["landmarks_ok"]
        frame_no    = _state["frame_no"]

    def fmt_dist(d):
        if d < 0:
            return f"{_DIM}  ---{_RST}"
        col = _R if d < DIST_THRESHOLD else _G
        return f"{col}{d:.3f}{_RST}"

    def fmt_vis(v):
        if v < 0:
            return f"{_DIM} ---{_RST}"
        col = _G if v >= VIS_THRESHOLD else _R
        return f"{col}{v:.2f}{_RST}"

    ref_label = f"{_Y}입(Mouth){_RST}" if USE_MOUTH else f"{_Y}코(Nose ){_RST}"

    bar_on  = int(min(counter, SUCCESS_FRAMES))
    bar_off = SUCCESS_FRAMES - bar_on
    bar_col = _G if detected else _B
    bar = f"{bar_col}{'█' * bar_on}{_DIM}{'░' * bar_off}{_RST}"

    lm_status = f"{_G}감지됨{_RST}" if landmarks_ok else f"{_R}없음  {_RST}"
    det_str   = f"  {_G}★ DETECTED!{_RST}" if detected else ""

    lines = [
        f"{_C}{'─'*50}{_RST}",
        f"  복약행위 감지 튜닝   frame #{frame_no}",
        f"{_C}{'─'*50}{_RST}",
        f"  기준점   : {ref_label}              [m]",
        f"  임계값   : {_Y}{DIST_THRESHOLD:.2f}{_RST}                  [+ / -]",
        f"  연속프레임: {_Y}{SUCCESS_FRAMES}{_RST}                    [] / []",
        f"  vis 임계값: {_Y}{VIS_THRESHOLD:.2f}{_RST}                  [v / V]",
        f"{_C}{'─'*50}{_RST}",
        f"  랜드마크  : {lm_status}",
        f"  vis nose : {fmt_vis(vis_nose)}   L wrist: {fmt_vis(vis_lw)}   R wrist: {fmt_vis(vis_rw)}",
        f"  dist  L  : {fmt_dist(dist_l)}   R: {fmt_dist(dist_r)}",
        f"  counter  : {bar} ({counter}/{SUCCESS_FRAMES}){det_str}",
        f"{_C}{'─'*50}{_RST}",
        f"  {_DIM}r=리셋  s=저장  q=종료{_RST}",
    ]

    sys.stdout.write(_CLR)
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


# ── 키 입력 처리 ─────────────────────────────────────────────────────────
def _handle_key(key):
    global DIST_THRESHOLD, SUCCESS_FRAMES, USE_MOUTH, VIS_THRESHOLD

    if key in ('+', '='):
        DIST_THRESHOLD = round(min(DIST_THRESHOLD + 0.01, 0.99), 2)
        _reset_counter()
    elif key == '-':
        DIST_THRESHOLD = round(max(DIST_THRESHOLD - 0.01, 0.05), 2)
        _reset_counter()
    elif key == ']':
        SUCCESS_FRAMES = min(SUCCESS_FRAMES + 1, 30)
        _reset_counter()
    elif key == '[':
        SUCCESS_FRAMES = max(SUCCESS_FRAMES - 1, 1)
        _reset_counter()
    elif key == 'v':
        VIS_THRESHOLD = round(min(VIS_THRESHOLD + 0.05, 1.0), 2)
        _reset_counter()
    elif key == 'V':
        VIS_THRESHOLD = round(max(VIS_THRESHOLD - 0.05, 0.0), 2)
        _reset_counter()
    elif key == 'm':
        USE_MOUTH = not USE_MOUTH
        _reset_counter()
    elif key == 'r':
        _reset_counter()
    elif key == 's':
        _save_to_behavior_thread(DIST_THRESHOLD, SUCCESS_FRAMES)
    elif key in ('q', 'Q', '\x03'):   # q, Q, Ctrl+C
        _state["running"] = False
        return False
    return True


def _reset_counter():
    with _lock:
        _state["counter"]  = 0
        _state["detected"] = False


# ── behavior_thread.py 저장 ──────────────────────────────────────────────
def _save_to_behavior_thread(threshold: float, frames: int):
    try:
        with open(_BEHAVIOR_THREAD_PATH, "r", encoding="utf-8") as f:
            src = f.read()
        src = re.sub(r"(_DIST_THRESHOLD\s*=\s*)[\d.]+", lambda m: f"{m.group(1)}{threshold}", src)
        src = re.sub(r"(_SUCCESS_FRAMES\s*=\s*)\d+",   lambda m: f"{m.group(1)}{frames}",    src)
        with open(_BEHAVIOR_THREAD_PATH, "w", encoding="utf-8") as f:
            f.write(src)
        # 저장 메시지는 다음 render에서 덮이므로 별도 출력
        sys.stdout.write(f"\n{_G}[SAVED] TH={threshold:.2f}  FRAMES={frames}{_RST}\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stdout.write(f"\n{_R}[SAVE ERROR] {e}{_RST}\n")
        sys.stdout.flush()


# ── 메인 ─────────────────────────────────────────────────────────────────
def run():
    # CSV 준비
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(_LOG_PATH)
    log_file = open(_LOG_PATH, "a", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)
    if write_header:
        log_writer.writerow([
            "session_time", "frame_no",
            "ref_point", "threshold", "success_frames", "vis_threshold",
            "dist_left", "dist_right", "min_dist",
            "is_near", "counter", "detected",
        ])

    # 포즈 처리 스레드 시작
    worker = threading.Thread(target=_pose_worker, args=(log_writer, log_file), daemon=True)
    worker.start()

    # 터미널 raw 모드로 전환 (SSH 키 입력을 즉시 받기 위해)
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())

    try:
        while _state["running"]:
            # 화면 갱신
            _render()

            # 키 입력 확인 (0.1초 타임아웃)
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                key = sys.stdin.read(1)
                if not _handle_key(key):
                    break

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        _state["running"] = False
        worker.join(timeout=2)
        log_file.close()

        sys.stdout.write(_CLR)
        print(f"최종 설정 — TH: {DIST_THRESHOLD:.2f}  FRAMES: {SUCCESS_FRAMES}"
              f"  VIS: {VIS_THRESHOLD:.2f}  기준점: {'입' if USE_MOUTH else '코'}")
        print(f"로그: {_LOG_PATH}")


if __name__ == "__main__":
    run()
