"""
비교 테스트: MediaPipe FaceMesh + Hands
판단 로직: 입(landmark 13) ↔ 검지 끝(landmark 8) 유클리드 거리
카메라: Raspberry Pi Camera Module 3 (Picamera2, BGR888)

키 조작:
  1 — 트라이얼 시작 (복약 행위 시작)
  2 — 트라이얼 중지 (미감지 처리)
  3 — 종료
"""
import csv
import logging
import os
import time
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np
from picamera2 import Picamera2

# ── 설정 ──────────────────────────────────────────────────────────────────────
INTAKE_DISTANCE_THRESHOLD = 0.10
SUCCESS_REQUIRED_FRAMES   = 5
PRINT_INTERVAL            = 30

# ── 로깅 설정 ─────────────────────────────────────────────────────────────────
_MODEL    = "mp_hands"
_LOG_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
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

# ── MediaPipe 초기화 ───────────────────────────────────────────────────────────
mp_draw      = mp.solutions.drawing_utils
mp_hands_mod = mp.solutions.hands
mp_face_mesh = mp.solutions.face_mesh

hands = mp_hands_mod.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.1,
    min_tracking_confidence=0.1,
)
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

# ── 카메라 초기화 ──────────────────────────────────────────────────────────────
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (640, 480)}
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
_trials     = []   # 트라이얼별 결과

_t0       = time.time()
_fps_list = []

_log.info("=" * 60)
_log.info("세션 시작  모델=%s", _MODEL)
_log.info("  threshold=%.2f  success_frames=%d", INTAKE_DISTANCE_THRESHOLD, SUCCESS_REQUIRED_FRAMES)
_log.info("  조작: 1=시작  2=중지  3=종료")
_log.info("  로그파일=%s", _LOG_FILE)
_log.info("=" * 60)
print(f"[{_MODEL}] 준비 완료  —  1:시작  2:중지  3:종료")
print(f"  로그 저장: {_LOG_FILE}")

try:
    while True:
        frame = picam2.capture_array()
        frame = cv2.flip(frame, 1)
        total_frames += 1
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        hand_res = hands.process(rgb)
        face_res = face_mesh.process(rgb)

        is_near      = False
        current_dist = 1.0

        # ── 랜드마크 추출 & 거리 계산 (항상 실행) ─────────────────────────
        if face_res.multi_face_landmarks:
            face_lm  = face_res.multi_face_landmarks[0]
            mouth    = face_lm.landmark[13]
            mouth_pt = (int(mouth.x * w), int(mouth.y * h))

            mp_draw.draw_landmarks(
                frame, face_lm,
                mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_draw.DrawingSpec(
                    color=(180, 180, 180), thickness=1),
            )
            cv2.circle(frame, mouth_pt, 6, (255, 255, 0), -1)

            if hand_res.multi_hand_landmarks:
                hand_lm   = hand_res.multi_hand_landmarks[0]
                finger    = hand_lm.landmark[8]
                finger_pt = (int(finger.x * w), int(finger.y * h))

                mp_draw.draw_landmarks(
                    frame, hand_lm, mp_hands_mod.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                    mp_draw.DrawingSpec(color=(0, 200, 0), thickness=2),
                )
                cv2.circle(frame, finger_pt, 6, (0, 255, 255), -1)
                current_dist = np.hypot(finger.x - mouth.x, finger.y - mouth.y)

                if current_dist < INTAKE_DISTANCE_THRESHOLD:
                    cv2.line(frame, mouth_pt, finger_pt, (0, 255, 0), 3)

        # ── 감지 로직 (ACTIVE 상태에서만) ────────────────────────────────
        if _state == STATE_ACTIVE:
            if face_res.multi_face_landmarks and hand_res.multi_hand_landmarks:
                if current_dist < INTAKE_DISTANCE_THRESHOLD:
                    intake_counter += 1
                    is_near = True
                else:
                    intake_counter = max(0, intake_counter - 1)
            else:
                intake_counter = max(0, intake_counter - 1)

            if is_near:
                near_frames += 1

            # 접근 시작
            if intake_counter >= 1 and _prev_cnt == 0:
                _approach_t = time.time()
                _fired      = False
                _log.info("  접근 시작  frame=%d  dist=%.4f", total_frames, current_dist)

            # 복약 감지
            if intake_counter >= SUCCESS_REQUIRED_FRAMES and not _fired:
                _fired        = True
                approach_dur  = (time.time() - _approach_t) if _approach_t else 0
                trial_dur     = time.time() - _trial_t
                _log.info("  *** 복약감지 ***  dist=%.4f  접근→감지=%.2fs  fps=%.1f",
                          current_dist, approach_dur, fps if total_frames > 1 else 0)
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

        # ── 키 입력 ───────────────────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key == ord('1') and _state == STATE_IDLE:
            intake_counter = 0
            _prev_cnt      = 0
            _approach_t    = None
            _fired         = False
            _trial_no     += 1
            _trial_t       = time.time()
            _state         = STATE_ACTIVE
            _log.info("Trial #%d 시작", _trial_no)

        elif key == ord('2') and _state == STATE_ACTIVE:
            trial_dur = time.time() - _trial_t
            _log.info("Trial #%d 중지 (미감지)  소요=%.2fs", _trial_no, trial_dur)
            _trials.append({
                "no": _trial_no, "detected": False,
                "duration_s": round(trial_dur, 2),
                "approach_s": None, "detect_dist": None,
            })
            intake_counter = 0
            _state         = STATE_IDLE

        elif key == ord('3') or key == 27:
            break

        # ── 화면 표시 ─────────────────────────────────────────────────────
        detected_cnt = sum(1 for t in _trials if t["detected"])
        color        = (0, 255, 0) if is_near else (0, 0, 255)

        if _state == STATE_ACTIVE:
            if intake_counter >= SUCCESS_REQUIRED_FRAMES:
                cv2.putText(frame, "INTAKE DETECTED!", (w // 2 - 170, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 0), 3)
            cv2.putText(frame, f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.putText(frame, f"FPS: {fps:.1f}",
                    (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Dist: {current_dist:.4f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # 상태 표시줄 (하단)
        state_label = f"[측정중] Trial #{_trial_no}  2:중지" if _state == STATE_ACTIVE \
                      else f"[대기중]  1:시작  |  성공 {detected_cnt}/{_trial_no}"
        state_color = (0, 255, 100) if _state == STATE_ACTIVE else (180, 180, 180)
        cv2.rectangle(frame, (0, h - 40), (w, h), (30, 30, 30), -1)
        cv2.putText(frame, state_label, (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, state_color, 2)
        cv2.putText(frame, "3:종료", (w - 80, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (100, 100, 255), 2)

        cv2.imshow("MP FaceMesh + Hands | Intake Detection", frame)

        if total_frames % PRINT_INTERVAL == 0 and _state == STATE_ACTIVE:
            print(f"[{total_frames:5d}f]  FPS={fps:5.1f}  dist={current_dist:.4f}"
                  f"  count={intake_counter}/{SUCCESS_REQUIRED_FRAMES}")

finally:
    duration      = time.time() - _t0
    avg_fps       = sum(_fps_list) / len(_fps_list) if _fps_list else 0
    min_fps       = min(_fps_list) if _fps_list else 0
    max_fps       = max(_fps_list) if _fps_list else 0
    total_trials  = len(_trials)
    detected_cnt  = sum(1 for t in _trials if t["detected"])
    success_rate  = detected_cnt / total_trials * 100 if total_trials else 0
    avg_det_dur   = (sum(t["duration_s"] for t in _trials if t["detected"]) / detected_cnt
                     if detected_cnt else 0)
    avg_app_s     = (sum(t["approach_s"] for t in _trials if t["approach_s"] is not None)
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
        result = f"✓  소요={t['duration_s']}s  접근→감지={t['approach_s']}s  dist={t['detect_dist']}" \
                 if t["detected"] else f"✗  소요={t['duration_s']}s (미감지)"
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

    print(f"\n종료  |  트라이얼 {total_trials}회  성공 {detected_cnt}회 ({success_rate:.1f}%)")
    print(f"로그 저장: {_LOG_FILE}")
    picam2.stop()
    cv2.destroyAllWindows()
    hands.close()
    face_mesh.close()
