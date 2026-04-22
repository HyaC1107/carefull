"""
비교 테스트: YOLO Pose 단독
판단 로직: 코(0) ↔ 왼손목(9) / 오른손목(10) 중 가까운 쪽 정규화 거리
모델: dev_test/models/yolo26n-pose_ncnn_model
카메라: Raspberry Pi Camera Module 3 (Picamera2, BGR888)
"""
import os
import time

import cv2
import numpy as np
from picamera2 import Picamera2

# ── 모델 경로 ──────────────────────────────────────────────────────────────────
_DIR       = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(_DIR, "..", "models", "yolo26n-pose_ncnn_model")

MODEL_IMGSZ = 640

# ── 설정 ──────────────────────────────────────────────────────────────────────
INTAKE_DISTANCE_THRESHOLD = 0.15
SUCCESS_REQUIRED_FRAMES   = 5
CONF_THRESHOLD            = 0.3
PRINT_INTERVAL            = 30

NOSE    = 0
L_WRIST = 9
R_WRIST = 10

# ── YOLO 모델 로드 ─────────────────────────────────────────────────────────────
from ultralytics import YOLO   # noqa: E402

model = YOLO(MODEL_PATH)

# ── 카메라 초기화 ──────────────────────────────────────────────────────────────
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (640, 480)}
))
picam2.start()

intake_counter = 0
total_frames   = 0
near_frames    = 0
prev_time      = time.time()

print("[YOLO Pose] 복약 행위 감지 시작  (ESC 종료)")
print(f"  model: {MODEL_PATH}")
print(f"  keypoints: nose={NOSE}, wrists={L_WRIST}/{R_WRIST}")
print(f"  threshold={INTAKE_DISTANCE_THRESHOLD}  success_frames={SUCCESS_REQUIRED_FRAMES}")

try:
    while True:
        frame = picam2.capture_array()          # BGR
        frame = cv2.flip(frame, 1)
        total_frames += 1
        h, w  = frame.shape[:2]

        results = model(frame, imgsz=MODEL_IMGSZ, verbose=False)

        is_near      = False
        current_dist = 1.0

        for r in results:
            if r.keypoints is None or len(r.keypoints.data) == 0:
                continue

            kps = r.keypoints.data[0]   # (17, 3): x_px, y_px, conf
            frame = r.plot()

            nose_kp    = kps[NOSE]
            l_wrist_kp = kps[L_WRIST]
            r_wrist_kp = kps[R_WRIST]

            if nose_kp[2] < CONF_THRESHOLD:
                break

            nose_n  = (nose_kp[0].item() / w, nose_kp[1].item() / h)
            nose_pt = (int(nose_kp[0].item()), int(nose_kp[1].item()))
            cv2.circle(frame, nose_pt, 8, (255, 255, 0), -1)

            dist_l = dist_r = 1.0
            lw_pt = rw_pt = nose_pt

            if l_wrist_kp[2] >= CONF_THRESHOLD:
                lw_n  = (l_wrist_kp[0].item() / w, l_wrist_kp[1].item() / h)
                lw_pt = (int(l_wrist_kp[0].item()), int(l_wrist_kp[1].item()))
                dist_l = np.hypot(lw_n[0] - nose_n[0], lw_n[1] - nose_n[1])
                cv2.circle(frame, lw_pt, 8, (0, 255, 255), -1)

            if r_wrist_kp[2] >= CONF_THRESHOLD:
                rw_n  = (r_wrist_kp[0].item() / w, r_wrist_kp[1].item() / h)
                rw_pt = (int(r_wrist_kp[0].item()), int(r_wrist_kp[1].item()))
                dist_r = np.hypot(rw_n[0] - nose_n[0], rw_n[1] - nose_n[1])
                cv2.circle(frame, rw_pt, 8, (0, 255, 255), -1)

            current_dist = min(dist_l, dist_r)
            closer_pt    = lw_pt if dist_l <= dist_r else rw_pt

            if current_dist < INTAKE_DISTANCE_THRESHOLD:
                intake_counter += 1
                is_near = True
                cv2.line(frame, nose_pt, closer_pt, (0, 255, 0), 3)
            else:
                intake_counter = max(0, intake_counter - 1)

            break

        if is_near:
            near_frames += 1

        curr_time = time.time()
        fps       = 1.0 / max(curr_time - prev_time, 1e-9)
        prev_time = curr_time

        color = (0, 255, 0) if is_near else (0, 0, 255)

        if intake_counter >= SUCCESS_REQUIRED_FRAMES:
            cv2.putText(frame, "INTAKE DETECTED!", (w // 2 - 170, 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 0), 3)

        cv2.putText(frame, f"FPS: {fps:.1f}",
                    (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Dist:  {current_dist:.4f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("YOLO Pose | Intake Detection", frame)

        if total_frames % PRINT_INTERVAL == 0:
            rate = near_frames / total_frames * 100
            print(f"[{total_frames:5d}f]  FPS={fps:5.1f}  감지율={rate:5.1f}%")

        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    rate = near_frames / max(total_frames, 1) * 100
    print(f"\n종료  |  총 {total_frames}프레임  |  복약 감지율: {rate:.1f}%")
    picam2.stop()
    cv2.destroyAllWindows()
