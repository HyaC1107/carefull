import cv2
import numpy as np
import time
from picamera2 import Picamera2
from ultralytics import YOLO

# ----------------------
# 1. YOLOv11 Nano 모델 설정
# ----------------------
# 팀장님이 커스텀 학습하여 양자화(INT8)한 모델의 경로를 지정합니다.
MODEL_PATH = "yolo11n_medication_int8.tflite" 

try:
    # Ultralytics는 tflite 포맷도 자동으로 인식하여 추론합니다.
    model = YOLO(MODEL_PATH)
    print(f"[{MODEL_PATH}] 모델 로드 완료!")
except Exception as e:
    print(f"모델 로드 에러: {e}")
    print("테스트용 기본 모델(yolo11n.pt)을 로드합니다.")
    model = YOLO("yolo11n.pt") # 테스트용 폴백

# 커스텀 학습 시 지정한 클래스 ID 매핑 (예시)
CLASS_MOUTH = 0
CLASS_HAND = 1
CLASS_PILL = 2

# ----------------------
# 2. 카메라 설정 (기존 유지)
# ----------------------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (640, 480)}
))
picam2.start()

# ----------------------
# 3. 복약 판정용 변수
# ----------------------
# 픽셀 기반 거리 임계값 (640x480 해상도 기준, 테스트하며 조절 필요)
INTAKE_DISTANCE_THRESHOLD = 70 
SUCCESS_REQUIRED_FRAMES = 5
intake_counter = 0

print("💊 YOLOv11 객체 인식 기반 복약 행위 감지 중...")
print("ESC를 누르면 종료")
prev_time = 0

try:
    while True:
        frame = picam2.capture_array()
        
        # FPS 계산
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if prev_time > 0 else 0
        prev_time = curr_time

        # ----------------------
        # 4. YOLO 추론 (Inference)
        # ----------------------
        # conf: 신뢰도 임계값(0.4 이하 무시), verbose=False: 터미널 로그 숨김
        results = model.predict(source=frame, conf=0.4, iou=0.45, verbose=False)
        
        mouth_center = None
        hand_center = None
        pill_center = None
        is_near = False
        current_dist = float('inf')

        # ----------------------
        # 5. 결과 파싱 및 시각화
        # ----------------------
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # 바운딩 박스 좌표 (좌상단 x1, y1 / 우하단 x2, y2)
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # 객체 중심점 계산
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                # 박스 및 텍스트 그리기 (객체별 색상 구분)
                if cls_id == CLASS_MOUTH:
                    mouth_center = (cx, cy)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, f"Mouth {conf:.2f}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 2)
                
                elif cls_id == CLASS_HAND:
                    hand_center = (cx, cy)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(frame, f"Hand {conf:.2f}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 2)
                
                elif cls_id == CLASS_PILL:
                    pill_center = (cx, cy)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    cv2.putText(frame, f"Pill {conf:.2f}", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 2)

        # ----------------------
        # 6. 복약 행위 판정 로직 (Collision Check)
        # ----------------------
        # 약(Pill)이 화면에 보이면 약을 타겟으로, 약이 안 보이면 손(Hand)을 타겟으로 설정
        target_center = pill_center if pill_center else hand_center

        if mouth_center and target_center:
            # 두 객체의 중심점 간 유클리디안 거리 계산
            current_dist = np.sqrt((mouth_center[0] - target_center[0])**2 + (mouth_center[1] - target_center[1])**2)
            
            # 거리가 임계값 이내로 들어오면 (충돌 발생)
            if current_dist < INTAKE_DISTANCE_THRESHOLD:
                intake_counter += 1
                is_near = True
                cv2.line(frame, mouth_center, target_center, (0, 255, 0), 3) # 연결선 그리기
            else:
                intake_counter = max(0, intake_counter - 1)
        else:
            intake_counter = max(0, intake_counter - 1)

        # ----------------------
        # 7. UI 오버레이 업데이트
        # ----------------------
        color = (0, 255, 0) if is_near else (0, 0, 255)
        
        if intake_counter >= SUCCESS_REQUIRED_FRAMES:
            cv2.putText(frame, "INTAKE COMPLETE!", (50, 100), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3)

        cv2.putText(frame, f"FPS: {int(fps)}", (640 - 120, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        dist_text = f"Dist: {int(current_dist)}px" if current_dist != float('inf') else "Dist: N/A"
        cv2.putText(frame, dist_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Count: {intake_counter}/{SUCCESS_REQUIRED_FRAMES}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("YOLOv11 Intake Detection", frame)

        if cv2.waitKey(1) & 0xFF == 27: # ESC로 종료
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()