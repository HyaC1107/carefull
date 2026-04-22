"""
비교 테스트: MediaPipe FaceMesh + Hands
판단 로직: 입(landmark 13) ↔ 검지 끝(landmark 8) 유클리드 거리
카메라: Raspberry Pi Camera Module 3 (Picamera2, BGR888)
"""
import time

import cv2
import mediapipe as mp
import numpy as np
from picamera2 import Picamera2

# ── 설정 ──────────────────────────────────────────────────────────────────────
INTAKE_DISTANCE_THRESHOLD = 0.10
SUCCESS_REQUIRED_FRAMES   = 5
PRINT_INTERVAL            = 30

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

intake_counter = 0
total_frames   = 0
near_frames    = 0
prev_time      = time.time()

print("[MP FaceMesh + Hands] 복약 행위 감지 시작  (ESC 종료)")
print(f"  threshold={INTAKE_DISTANCE_THRESHOLD}  success_frames={SUCCESS_REQUIRED_FRAMES}")

try:
    while True:
        frame = picam2.capture_array()          # BGR
        frame = cv2.flip(frame, 1)
        total_frames += 1
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        hand_res = hands.process(rgb)
        face_res = face_mesh.process(rgb)

        is_near      = False
        current_dist = 1.0

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
                    intake_counter += 1
                    is_near = True
                    cv2.line(frame, mouth_pt, finger_pt, (0, 255, 0), 3)
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

        cv2.imshow("MP FaceMesh + Hands | Intake Detection", frame)

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
    hands.close()
    face_mesh.close()
