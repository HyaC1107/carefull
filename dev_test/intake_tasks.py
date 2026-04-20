import cv2
import numpy as np
import os
import time
from picamera2 import Picamera2

# ----------------------
# MediaPipe Tasks API (신버전)
# ----------------------
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.components import containers as mp_containers
import mediapipe as mp

# 시각화 유틸 (Tasks API에서도 그대로 사용 가능)
mp_draw = mp.solutions.drawing_utils
mp_draw_styles = mp.solutions.drawing_styles

# ----------------------
# 모델 파일 경로 설정
# Tasks API는 .task 또는 .tflite 모델 파일이 필요합니다.
# 아래 명령어로 다운로드하세요:
#   wget -q https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
#   wget -q https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
# ----------------------
HAND_MODEL_PATH = "hand_landmarker.task"
FACE_MODEL_PATH = "face_landmarker.task"

# 모델 파일 존재 여부 확인
for path, name in [(HAND_MODEL_PATH, "Hand"), (FACE_MODEL_PATH, "Face")]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"[오류] {name} 모델 파일 없음: '{path}'\n"
            f"아래 명령어로 다운로드하세요:\n"
            f"  wget -q https://storage.googleapis.com/mediapipe-models/"
            + ("hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
               if name == "Hand"
               else "face_landmarker/face_landmarker/float16/latest/face_landmarker.task")
        )

# ----------------------
# Hand Landmarker 설정
# ----------------------
hand_base_options = mp_tasks.BaseOptions(model_asset_path=HAND_MODEL_PATH)
hand_options = mp_vision.HandLandmarkerOptions(
    base_options=hand_base_options,
    running_mode=mp_vision.RunningMode.VIDEO,   # 비디오 스트림 모드
    num_hands=1,                                 # 한 손만 감지
    min_hand_detection_confidence=0.1,           # 기존 코드와 동일하게 낮게 유지
    min_hand_presence_confidence=0.1,
    min_tracking_confidence=0.1,
)
hand_landmarker = mp_vision.HandLandmarker.create_from_options(hand_options)

# ----------------------
# Face Landmarker 설정
# ----------------------
face_base_options = mp_tasks.BaseOptions(model_asset_path=FACE_MODEL_PATH)
face_options = mp_vision.FaceLandmarkerOptions(
    base_options=face_base_options,
    running_mode=mp_vision.RunningMode.VIDEO,   # 비디오 스트림 모드
    num_faces=1,
    min_face_detection_confidence=0.5,
    min_face_presence_confidence=0.5,
    min_tracking_confidence=0.5,
    output_face_blendshapes=False,               # 복약 검증에 불필요하므로 False
    output_facial_transformation_matrixes=False,
)
face_landmarker = mp_vision.FaceLandmarker.create_from_options(face_options)

# ----------------------
# 랜드마크 -> 픽셀 좌표 변환 헬퍼
# Tasks API는 NormalizedLandmark 객체를 반환하므로 동일하게 x, y 접근 가능
# ----------------------
def to_pixel(landmark, w, h):
    return (int(landmark.x * w), int(landmark.y * h))

# ----------------------
# 카메라 설정 (기존 Picamera2 설정 유지)
# ----------------------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

# ----------------------
# 복약 판정용 변수 (기존과 동일)
# ----------------------
INTAKE_DISTANCE_THRESHOLD = 0.10
SUCCESS_REQUIRED_FRAMES = 5
intake_counter = 0

# Tasks API VIDEO 모드는 타임스탬프(ms)를 직접 넘겨야 함
start_time = time.time()

print("복약 행위 감지 중... (손을 입 근처로 가져가세요)")
print("ESC를 누르면 종료")

prev_time = time.time()

try:
    while True:
        # 1. 프레임 캡처
        frame = picam2.capture_array()

        # 2. FPS 계산
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time + 1e-9)
        prev_time = curr_time

        # 3. 색상 변환 + 좌우 반전
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = cv2.flip(rgb, 1)
        h, w, _ = rgb.shape

        # 4. Tasks API용 타임스탬프 계산 (ms 단위 정수)
        timestamp_ms = int((curr_time - start_time) * 1000)

        # 5. Tasks API는 mp.Image 객체로 입력받음
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        # 6. 추론 실행 (VIDEO 모드: detect_for_video 사용)
        hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
        face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)

        # 7. 그리기용 프레임 (RGB 그대로 사용, 나중에 imshow에서 BGR 변환)
        display_frame = rgb.copy()

        is_near = False
        current_dist = 1.0

        # 8. 얼굴 랜드마크 처리
        # Tasks API: face_result.face_landmarks -> list[list[NormalizedLandmark]]
        mouth_landmark = None
        if face_result.face_landmarks:
            face_lms = face_result.face_landmarks[0]  # 첫 번째 얼굴

            # 입 중앙 (13번 - 기존 코드와 동일)
            mouth_landmark = face_lms[13]
            mouth_coords = to_pixel(mouth_landmark, w, h)

            # 얼굴 메쉬 그리기
            # Tasks API는 draw_landmarks에 호환되는 NormalizedLandmarkList가 아니므로
            # 직접 점으로 시각화
            for lm in face_lms:
                px, py = to_pixel(lm, w, h)
                cv2.circle(display_frame, (px, py), 1, (200, 200, 200), -1)

            # 입 중앙 포인트 강조
            cv2.circle(display_frame, mouth_coords, 5, (255, 255, 0), -1)

        # 9. 손 랜드마크 처리
        # Tasks API: hand_result.hand_landmarks -> list[list[NormalizedLandmark]]
        if mouth_landmark is not None and hand_result.hand_landmarks:
            hand_lms = hand_result.hand_landmarks[0]  # 첫 번째 손

            # 검지 끝 (Landmark 8 - 기존 코드와 동일)
            finger_tip = hand_lms[8]
            finger_coords = to_pixel(finger_tip, w, h)

            # 손 랜드마크 및 연결선 그리기
            # HAND_CONNECTIONS는 mp.solutions.hands에서 그대로 가져올 수 있음
            hand_connections = mp.solutions.hands.HAND_CONNECTIONS
            for connection in hand_connections:
                start_lm = hand_lms[connection[0]]
                end_lm = hand_lms[connection[1]]
                cv2.line(
                    display_frame,
                    to_pixel(start_lm, w, h),
                    to_pixel(end_lm, w, h),
                    (0, 200, 0), 2
                )
            for lm in hand_lms:
                cv2.circle(display_frame, to_pixel(lm, w, h), 3, (0, 255, 0), -1)

            # 검지 끝 강조
            cv2.circle(display_frame, finger_coords, 5, (0, 255, 255), -1)

            # 10. 유클리드 거리 계산 (정규화 좌표 기준 - 기존 로직 동일)
            current_dist = np.sqrt(
                (finger_tip.x - mouth_landmark.x) ** 2 +
                (finger_tip.y - mouth_landmark.y) ** 2
            )

            # 11. 복약 행위 판정 로직 (기존 동일)
            if current_dist < INTAKE_DISTANCE_THRESHOLD:
                intake_counter += 1
                is_near = True
                cv2.line(display_frame, mouth_coords, finger_coords, (0, 255, 0), 3)
            else:
                intake_counter = max(0, intake_counter - 1)

        # 12. 결과 시각화 (기존 동일)
        color = (0, 255, 0) if is_near else (0, 0, 255)

        if intake_counter >= SUCCESS_REQUIRED_FRAMES:
            cv2.putText(display_frame, "INTAKE COMPLETE!", (50, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

        cv2.putText(display_frame, f"FPS: {int(fps)}", (w - 120, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(display_frame, f"Dist: {current_dist:.4f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(display_frame, f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # 13. BGR 변환 후 출력 (OpenCV imshow는 BGR 기대)
        cv2.imshow("Intake Detection", cv2.cvtColor(display_frame, cv2.COLOR_RGB2BGR))

        if cv2.waitKey(1) & 0xFF == 27:  # ESC 종료
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
    # Tasks API는 close() 대신 __exit__ / with문 사용 권장이지만
    # 명시적 해제도 가능
    hand_landmarker.close()
    face_landmarker.close()