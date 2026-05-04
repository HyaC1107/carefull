"""
비교 테스트: YOLO Pose (순수 NCNN — ultralytics/PyTorch 불필요)
판단 로직: 코(0) ↔ 왼손목(9) / 오른손목(10) 중 가까운 쪽 정규화 거리
모델: dev_test/models/yolo26n-pose_ncnn_model (model.ncnn.param / .bin)
카메라: Raspberry Pi Camera Module 3 (Picamera2, RGB888)

설치:
  pip install ncnn opencv-python numpy

실행 방법 (SSH):
  export DISPLAY=:0
  python test_yolo_pose.py

키 조작 (SSH 터미널):
  1 — 트라이얼 시작 (복약 행위 시작)
  2 — 트라이얼 중지 (미감지 처리)
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
import ncnn
import numpy as np
from picamera2 import Picamera2

# ── 모델 경로 ──────────────────────────────────────────────────────────────────
_DIR       = os.path.dirname(os.path.abspath(__file__))
_MODEL_DIR = os.path.join(_DIR, "..", "models", "yolo26n-pose_ncnn_model")
PARAM_PATH = os.path.join(_MODEL_DIR, "model.ncnn.param")
BIN_PATH   = os.path.join(_MODEL_DIR, "model.ncnn.bin")
MODEL_IMGSZ = 640

# ── 설정 ──────────────────────────────────────────────────────────────────────
INTAKE_DISTANCE_THRESHOLD = 0.30
SUCCESS_REQUIRED_FRAMES   = 5
CONF_THRESHOLD            = 0.3
IOU_THRESHOLD             = 0.45
KP_CONF_MIN               = 0.3
_WIN = "YOLO Pose NCNN | Intake Detection"

NOSE    = 0
L_WRIST = 9
R_WRIST = 10

_SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

# ── NCNN 모델 로드 ─────────────────────────────────────────────────────────────
_net = ncnn.Net()
_net.opt.use_vulkan_compute = False
_net.load_param(PARAM_PATH)
_net.load_model(BIN_PATH)


# ── 추론 헬퍼 ─────────────────────────────────────────────────────────────────
def _letterbox(img_bgr, target=MODEL_IMGSZ):
    h, w = img_bgr.shape[:2]
    scale = min(target / h, target / w)
    nh, nw = int(round(h * scale)), int(round(w * scale))
    resized = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
    pt, pl = (target - nh) // 2, (target - nw) // 2
    padded = np.full((target, target, 3), 114, dtype=np.uint8)
    padded[pt:pt + nh, pl:pl + nw] = resized
    return padded, scale, pt, pl


def _infer_frame(img_bgr):
    """BGR 이미지 → (pred_array, scale, pt, pl)"""
    padded, scale, pt, pl = _letterbox(img_bgr)
    # BGR→RGB, HWC→CHW, /255
    blob = np.ascontiguousarray(
        padded[:, :, ::-1].astype(np.float32).transpose(2, 0, 1) / 255.0
    )
    mat_in = ncnn.Mat(blob)
    with _net.create_extractor() as ex:
        ex.input("in0", mat_in)
        _, mat_out = ex.extract("out0")
    return np.array(mat_out), scale, pt, pl


def _decode(pred, orig_w, orig_h, scale, pt, pl):
    """
    pred: (56, 8400) 또는 (8400, 56)
    반환: {kps_raw, kps_norm, box, conf} 또는 None
    """
    if pred.ndim != 2:
        return None
    if pred.shape[0] == 56:
        pred = pred.T           # → (8400, 56)
    elif pred.shape[1] != 56:
        return None

    confs = pred[:, 4]
    filt  = pred[confs > CONF_THRESHOLD]
    if len(filt) == 0:
        return None

    idxs = cv2.dnn.NMSBoxes(
        filt[:, :4].tolist(), filt[:, 4].tolist(), CONF_THRESHOLD, IOU_THRESHOLD
    )
    if len(idxs) == 0:
        return None
    i = int(idxs[0]) if not hasattr(idxs[0], '__len__') else int(idxs[0][0])

    kps_raw = filt[i, 5:].reshape(17, 3)   # x640, y640, vis

    def _to_norm(kp):
        x_n = float(np.clip((kp[0] - pl) / (scale * orig_w), 0.0, 1.0))
        y_n = float(np.clip((kp[1] - pt) / (scale * orig_h), 0.0, 1.0))
        return x_n, y_n, float(kp[2])

    return {
        "kps_raw":  kps_raw,
        "kps_norm": [_to_norm(kps_raw[j]) for j in range(17)],
        "conf":     float(filt[i, 4]),
        "scale": scale, "pt": pt, "pl": pl,
    }


def _draw_pose(disp, det):
    scale, pt, pl = det["scale"], det["pt"], det["pl"]
    pts = [
        (int(round((kp[0] - pl) / scale)),
         int(round((kp[1] - pt) / scale)),
         float(kp[2]))
        for kp in det["kps_raw"]
    ]
    for a, b in _SKELETON:
        if pts[a][2] >= KP_CONF_MIN and pts[b][2] >= KP_CONF_MIN:
            cv2.line(disp, pts[a][:2], pts[b][:2], (0, 200, 0), 2)
    for x, y, v in pts:
        if v >= KP_CONF_MIN:
            cv2.circle(disp, (x, y), 4, (0, 255, 0), -1)


# ── 터미널 non-blocking 입력 (SSH 키보드) ─────────────────────────────────────
class _TermInput:
    def __init__(self):
        self._fd  = sys.stdin.fileno()
        self._old = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)

    def read(self):
        if select.select([sys.stdin], [], [], 0)[0]:
            return os.read(self._fd, 1).decode('utf-8', errors='ignore')
        return None

    def restore(self):
        termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)


# ── 로깅 설정 ─────────────────────────────────────────────────────────────────
_MODEL    = "yolo_pose_ncnn"
_LOG_DIR  = os.path.join(_DIR, "logs")
os.makedirs(_LOG_DIR, exist_ok=True)
_TAG      = datetime.now().strftime("%Y%m%d_%H%M%S")
_LOG_FILE = os.path.join(_LOG_DIR, f"{_TAG}_{_MODEL}.log")
_CSV_FILE = os.path.join(_LOG_DIR, "summary.csv")

_log = logging.getLogger(_MODEL)
_log.setLevel(logging.DEBUG)
_fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
_log.addHandler(_fh)
_ch = logging.StreamHandler()
_ch.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
_log.addHandler(_ch)

# ── 카메라 초기화 ──────────────────────────────────────────────────────────────
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (640, 480)}
))
picam2.start()

# ── 상태 변수 ─────────────────────────────────────────────────────────────────
STATE_IDLE   = "IDLE"
STATE_ACTIVE = "ACTIVE"

intake_counter = 0
total_frames   = 0
near_frames    = 0
prev_time      = time.time()

_state      = STATE_IDLE
_trial_no   = 0
_trial_t    = None
_approach_t = None
_fired      = False
_prev_cnt   = 0
_trials     = []

_t0       = time.time()
_fps_list = []

_log.info("=" * 60)
_log.info("세션 시작  모델=%s", _MODEL)
_log.info("  threshold=%.2f  success_frames=%d  conf=%.2f",
          INTAKE_DISTANCE_THRESHOLD, SUCCESS_REQUIRED_FRAMES, CONF_THRESHOLD)
_log.info("  keypoints: nose=%d  wrists=%d/%d", NOSE, L_WRIST, R_WRIST)
_log.info("  param=%s", PARAM_PATH)
_log.info("  조작: 1=시작  2=중지  3=종료")
_log.info("  로그파일=%s", _LOG_FILE)
_log.info("=" * 60)
print(f"\n[{_MODEL}] 준비 완료  —  SSH 터미널: 1=시작  2=중지  3=종료")
print(f"  로그: {_LOG_FILE}\n")

_term = _TermInput()

cv2.namedWindow(_WIN, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(_WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

try:
    fps = 0.0
    while True:
        frame = picam2.capture_array()         # RGB (RGB888)
        frame = cv2.flip(frame, 1)
        total_frames += 1
        h, w  = frame.shape[:2]

        disp = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # ── NCNN 추론 ──────────────────────────────────────────────────────
        pred, scale, pt, pl = _infer_frame(disp)
        det = _decode(pred, w, h, scale, pt, pl)

        is_near      = False
        current_dist = 1.0
        kp_detected  = False

        if det is not None:
            kps_norm = det["kps_norm"]
            nose_n    = kps_norm[NOSE]
            l_wrist_n = kps_norm[L_WRIST]
            r_wrist_n = kps_norm[R_WRIST]

            _draw_pose(disp, det)

            nose_pt = (int(nose_n[0] * w),    int(nose_n[1] * h))
            lw_pt   = (int(l_wrist_n[0] * w), int(l_wrist_n[1] * h))
            rw_pt   = (int(r_wrist_n[0] * w), int(r_wrist_n[1] * h))
            cv2.circle(disp, nose_pt, 8, (255, 255,   0), -1)
            cv2.circle(disp, lw_pt,   8, (  0, 255, 255), -1)
            cv2.circle(disp, rw_pt,   8, (  0, 255, 255), -1)

            if nose_n[2] >= KP_CONF_MIN:
                kp_detected = True
                dist_l = (float(np.hypot(l_wrist_n[0] - nose_n[0], l_wrist_n[1] - nose_n[1]))
                          if l_wrist_n[2] >= KP_CONF_MIN else 1.0)
                dist_r = (float(np.hypot(r_wrist_n[0] - nose_n[0], r_wrist_n[1] - nose_n[1]))
                          if r_wrist_n[2] >= KP_CONF_MIN else 1.0)

                if dist_l < dist_r:
                    current_dist = dist_l
                    closer_pt    = lw_pt
                else:
                    current_dist = dist_r
                    closer_pt    = rw_pt

                if current_dist < INTAKE_DISTANCE_THRESHOLD:
                    is_near = True
                    cv2.line(disp, nose_pt, closer_pt, (0, 255, 0), 3)

        # ── 감지 로직 (ACTIVE 상태에서만) ────────────────────────────────
        if _state == STATE_ACTIVE:
            if kp_detected:
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
                _fired      = False
                _log.info("  접근 시작  frame=%d  dist=%.4f", total_frames, current_dist)

            if intake_counter >= SUCCESS_REQUIRED_FRAMES and not _fired:
                _fired       = True
                approach_dur = (time.time() - _approach_t) if _approach_t else 0
                trial_dur    = time.time() - _trial_t
                _log.info("  *** 복약감지 ***  dist=%.4f  접근→감지=%.2fs  fps=%.1f",
                          current_dist, approach_dur, fps)
                _log.info("Trial #%d 완료 ✓  소요=%.2fs", _trial_no, trial_dur)
                _trials.append({
                    "no": _trial_no, "detected": True,
                    "duration_s": round(trial_dur, 2),
                    "approach_s": round(approach_dur, 2),
                    "detect_dist": round(current_dist, 4),
                })
                intake_counter = 0
                _state         = STATE_IDLE

            _prev_cnt = intake_counter

        # ── FPS ───────────────────────────────────────────────────────────
        curr_time = time.time()
        fps       = 1.0 / max(curr_time - prev_time, 1e-9)
        prev_time = curr_time
        _fps_list.append(fps)

        # ── SSH 키 입력 ───────────────────────────────────────────────────
        key = _term.read()

        if key == '1' and _state == STATE_IDLE:
            intake_counter = 0
            _prev_cnt      = 0
            _approach_t    = None
            _fired         = False
            _trial_no     += 1
            _trial_t       = time.time()
            _state         = STATE_ACTIVE
            _log.info("Trial #%d 시작", _trial_no)

        elif key == '2' and _state == STATE_ACTIVE:
            trial_dur = time.time() - _trial_t
            _log.info("Trial #%d 중지 (미감지)  소요=%.2fs", _trial_no, trial_dur)
            _trials.append({
                "no": _trial_no, "detected": False,
                "duration_s": round(trial_dur, 2),
                "approach_s": None, "detect_dist": None,
            })
            intake_counter = 0
            _state         = STATE_IDLE

        elif key == '3':
            break

        # ── Pi 화면 표시 ──────────────────────────────────────────────────
        detected_cnt = sum(1 for t in _trials if t["detected"])
        color        = (0, 255, 0) if is_near else (0, 0, 255)

        if _state == STATE_ACTIVE and intake_counter >= SUCCESS_REQUIRED_FRAMES:
            cv2.putText(disp, "INTAKE DETECTED!", (w // 2 - 170, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 0), 3)

        cv2.putText(disp, f"FPS: {fps:.1f}",
                    (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(disp, f"Dist: {current_dist:.4f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        if _state == STATE_ACTIVE:
            cv2.putText(disp, f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        state_label = (f"[ACTIVE] Trial #{_trial_no}  Det:{detected_cnt}/{_trial_no}  SSH:2=stop 3=quit"
                       if _state == STATE_ACTIVE else
                       f"[IDLE]  Det:{detected_cnt}/{_trial_no}  SSH:1=start 3=quit")
        state_color = (0, 255, 100) if _state == STATE_ACTIVE else (180, 180, 180)
        cv2.rectangle(disp, (0, h - 36), (w, h), (30, 30, 30), -1)
        cv2.putText(disp, state_label, (8, h - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, state_color, 2)

        cv2.imshow(_WIN, disp)
        cv2.waitKey(1)

        t_status = (f"\r[측정중] Trial#{_trial_no}  dist={current_dist:.4f}  "
                    f"cnt={intake_counter}/{SUCCESS_REQUIRED_FRAMES}  fps={fps:.1f}  "
                    f"성공={detected_cnt}/{_trial_no}  | 2:중지 3:종료  "
                    if _state == STATE_ACTIVE else
                    f"\r[대기중]  dist={current_dist:.4f}  fps={fps:.1f}  "
                    f"성공={detected_cnt}/{_trial_no}  | 1:시작 3:종료          ")
        print(t_status, end="", flush=True)

finally:
    _term.restore()
    print()

    duration     = time.time() - _t0
    avg_fps      = sum(_fps_list) / len(_fps_list) if _fps_list else 0
    min_fps      = min(_fps_list) if _fps_list else 0
    max_fps      = max(_fps_list) if _fps_list else 0
    total_trials = len(_trials)
    detected_cnt = sum(1 for t in _trials if t["detected"])
    success_rate = detected_cnt / total_trials * 100 if total_trials else 0
    avg_det_dur  = (sum(t["duration_s"] for t in _trials if t["detected"]) / detected_cnt
                    if detected_cnt else 0)
    avg_app_s    = (sum(t["approach_s"] for t in _trials if t["approach_s"] is not None)
                    / detected_cnt if detected_cnt else 0)

    _log.info("=" * 60)
    _log.info("세션 종료")
    _log.info("  모델          : %s", _MODEL)
    _log.info("  총 시간       : %.1f 초", duration)
    _log.info("  총 프레임     : %d  (평균 FPS %.1f / min %.1f / max %.1f)",
              total_frames, avg_fps, min_fps, max_fps)
    _log.info("  트라이얼      : %d 회  성공 %d 회  성공률 %.1f%%",
              total_trials, detected_cnt, success_rate)
    _log.info("  평균 감지시간 : %.2f 초 (트라이얼 시작→감지)", avg_det_dur)
    _log.info("  평균 접근시간 : %.2f 초 (접근 시작→감지)", avg_app_s)
    _log.info("  트라이얼 상세:")
    for t in _trials:
        result = (f"✓  소요={t['duration_s']}s  접근→감지={t['approach_s']}s  dist={t['detect_dist']}"
                  if t["detected"] else f"✗  소요={t['duration_s']}s (미감지)")
        _log.info("    [#%d] %s", t["no"], result)
    _log.info("=" * 60)

    csv_exists = os.path.exists(_CSV_FILE)
    with open(_CSV_FILE, "a", newline="", encoding="utf-8") as f:
        cw = csv.writer(f)
        if not csv_exists:
            cw.writerow(["timestamp", "model", "duration_s", "total_frames",
                         "avg_fps", "min_fps", "max_fps",
                         "total_trials", "detected", "success_rate_pct",
                         "avg_detect_s", "avg_approach_s",
                         "threshold", "success_frames"])
        cw.writerow([_TAG, _MODEL, round(duration, 1), total_frames,
                     round(avg_fps, 1), round(min_fps, 1), round(max_fps, 1),
                     total_trials, detected_cnt, round(success_rate, 1),
                     round(avg_det_dur, 2), round(avg_app_s, 2),
                     INTAKE_DISTANCE_THRESHOLD, SUCCESS_REQUIRED_FRAMES])

    print(f"종료  |  트라이얼 {total_trials}회  성공 {detected_cnt}회 ({success_rate:.1f}%)")
    print(f"로그: {_LOG_FILE}")

    cv2.destroyAllWindows()
    picam2.stop()
    _net.clear()
