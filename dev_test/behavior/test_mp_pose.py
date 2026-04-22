"""
비교 테스트: MediaPipe Pose 단독
판단 로직: 코(0) ↔ 왼손목(15) / 오른손목(16) 중 가까운 쪽 거리
카메라: Raspberry Pi Camera Module 3 (Picamera2, BGR888)
"""
import time

import cv2
import mediapipe as mp
import numpy as np
from picamera2 import Picamera2

# ── 설정 ──────────────────────────────────────────────────────────────────────
INTAKE_DISTANCE_THRESHOLD = 0.15
SUCCESS_REQUIRED_FRAMES   = 5
PRINT_INTERVAL            = 30

NOSE    = 0
L_WRIST = 15
R_WRIST = 16

# ── MediaPipe 초기화 ───────────────────────────────────────────────────────────
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)

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

print("[MP Pose] 복약 행위 감지 시작  (ESC 종료)")
print(f"  keypoints: nose={NOSE}, wrists={L_WRIST}/{R_WRIST}")
print(f"  threshold={INTAKE_DISTANCE_THRESHOLD}  success_frames={SUCCESS_REQUIRED_FRAMES}")

try:
    while True:
        frame = picam2.capture_array()          # BGR
        frame = cv2.flip(frame, 1)
        total_frames += 1
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = pose.process(rgb)

        is_near      = False
        current_dist = 1.0

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            mp_draw.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                mp_draw.DrawingSpec(color=(0, 200, 0), thickness=2),
            )

            nose    = lm[NOSE]
            l_wrist = lm[L_WRIST]
            r_wrist = lm[R_WRIST]

            nose_pt = (int(nose.x * w),    int(nose.y * h))
            lw_pt   = (int(l_wrist.x * w), int(l_wrist.y * h))
            rw_pt   = (int(r_wrist.x * w), int(r_wrist.y * h))

            cv2.circle(frame, nose_pt, 8, (255, 255,   0), -1)
            cv2.circle(frame, lw_pt,   8, (  0, 255, 255), -1)
            cv2.circle(frame, rw_pt,   8, (  0, 255, 255), -1)

            dist_l = np.hypot(l_wrist.x - nose.x, l_wrist.y - nose.y)
            dist_r = np.hypot(r_wrist.x - nose.x, r_wrist.y - nose.y)

            if dist_l < dist_r:
                current_dist = dist_l
                closer_pt    = lw_pt
            else:
                current_dist = dist_r
                closer_pt    = rw_pt

            if current_dist < INTAKE_DISTANCE_THRESHOLD:
                intake_counter += 1
                is_near = True
                cv2.line(frame, nose_pt, closer_pt, (0, 255, 0), 3)
            else:
                intake_counter = max(0, intake_counter - 1)

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

        cv2.imshow("MP Pose | Intake Detection", frame)

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
    pose.close()
