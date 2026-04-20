import cv2
import numpy as np
import mediapipe as mp
import os
from picamera2 import Picamera2
import time

# ----------------------
# MediaPipe 시각화 툴 설정 (추가됨!)
# ----------------------
mp_draw = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,     # 비디오 스트림 모드 유지
    max_num_hands=1,            # 복약은 한 손으로 하니까 1개만 집중
    min_detection_confidence=0.1, # ⭐ 중요! 0.5 -> 0.3으로 낮춤 (더 쉽게 검출)
    min_tracking_confidence=0.1   # ⭐ 중요! 0.5 -> 0.3으로 낮춤 (추적 성능 향상)
)

# 얼굴 검출 대신, 입 위치를 더 정확히 잡기 위해 Face Mesh 사용 추천 (수정됨!)
# 만약 Face Detection을 고수하고 싶으시면 mp_face로 다시 바꾸셔도 됩니다.
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True, # 입술, 눈 등 정밀 랜드마크 포함
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# ----------------------
# 카메라 설정 (기존 Picamera2 설정 유지)
# ----------------------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

# 복약 판정용 변수
INTAKE_DISTANCE_THRESHOLD = 0.10  # 손-입 거리 임계값 (Face Mesh 기준으로 조정)
SUCCESS_REQUIRED_FRAMES = 5     # 15프레임 이상 유지 시 성공
intake_counter = 0

print(" 복약 행위 감지 중... (손을 입 근처로 가져가세요)")
print(" ESC를 누르면 종료")
prev_time = 0
curr_time = 0
try:
    while True:
        # 1. Picamera2에서 프레임 캡처
        frame = picam2.capture_array()
        # 2. FPS 계산
        curr_time = time.time() # 현재 시간
        fps = 1 / (curr_time - prev_time) # 1초 / 걸린 시간
        prev_time = curr_time # 이전 시간 업데이트

        # 2. 색상 채널 교정: BGR -> RGB (OpenCV는 BGR, MediaPipe는 RGB 사용)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 3. 좌우 반전 (거울 모드) - 선택 사항
        rgb = cv2.flip(rgb, 1)
        h, w, _ = rgb.shape

        # 4. 프로세싱
        hand_results = hands.process(rgb)
        face_results = face_mesh.process(rgb)

        is_near = False
        current_dist = 1.0

        # 5. 시각화용 프레임 준비: 다시 BGR로 돌려서 OpenCV가 그리게 함 (수정됨!)
        display_frame =rgb
        # 6. 얼굴(Face Mesh) 랜드마크 추출 및 그리기
        if face_results.multi_face_landmarks:
            face_landmarks = face_results.multi_face_landmarks[0]
            
            # 입 위치 지정 (예: 13번 포인트 - 윗입술 중앙 아래)
            mouth_center = face_landmarks.landmark[13]
            mouth_coords = (int(mouth_center.x * w), int(mouth_center.y * h))
            
            # 얼굴 랜드마크 그리기 (메쉬 형태)
            mp_draw.draw_landmarks(
                image=display_frame,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_draw.DrawingSpec(color=(200, 200, 200), thickness=1, circle_radius=1)
            )
            
            # 입 중앙에 점 그리기 (디버깅용)
            cv2.circle(display_frame, mouth_coords, 5, (255, 255, 0), -1)

            # 7. 손(Hands) 랜드마크 추출 및 그리기
            if hand_results.multi_hand_landmarks:
                hand_landmarks = hand_results.multi_hand_landmarks[0]
                
                # 검지 손가락 끝 (Landmark 8)
                finger_tip = hand_landmarks.landmark[8]
                finger_coords = (int(finger_tip.x * w), int(finger_tip.y * h))
                
                # 손 랜드마크 및 연결선 그리기
                mp_draw.draw_landmarks(
                    image=display_frame,
                    landmark_list=hand_landmarks,
                    connections=mp_hands.HAND_CONNECTIONS,
                    landmark_drawing_spec=mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    connection_drawing_spec=mp_draw.DrawingSpec(color=(0, 200, 0), thickness=2)
                )
                
                # 검지 끝에 점 그리기 (디버깅용)
                cv2.circle(display_frame, finger_coords, 5, (0, 255, 255), -1)

                # 8. 유클리드 거리 계산 (정규화된 좌표 기준)
                current_dist = np.sqrt((finger_tip.x - mouth_center.x)**2 + (finger_tip.y - mouth_center.y)**2)

                # 9. 복약 행위 판정 로직
                if current_dist < INTAKE_DISTANCE_THRESHOLD:
                    intake_counter += 1
                    is_near = True
                    # 손과 입 사이를 잇는 선 그리기
                    cv2.line(display_frame, mouth_coords, finger_coords, (0, 255, 0), 3)
                else:
                    intake_counter = max(0, intake_counter - 1) # 서서히 줄어들게

        # 10. 결과 시각화
        color = (0, 255, 0) if is_near else (0, 0, 255)
        
        # 복약 완료 판정
        if intake_counter >= SUCCESS_REQUIRED_FRAMES:
            cv2.putText(display_frame, "INTAKE COMPLETE!", (50, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

        cv2.putText(display_frame, f"FPS: {int(fps)}", (w - 120, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Dist: {current_dist:.4f}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(display_frame, f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("Intake Detection", display_frame)

        if cv2.waitKey(1) & 0xFF == 27: # ESC 종료
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
    hands.close()
    face_mesh.close()