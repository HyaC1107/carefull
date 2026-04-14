import cv2
import mediapipe as mp
import numpy as np

class IntakeDetector:
    def __init__(self):
        # Hands 모델 설정
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Face Detection 모델 설정
        self.mp_face = mp.solutions.face_detection
        self.face_detection = self.mp_face.FaceDetection(
            model_selection=0, # 근거리용
            min_detection_confidence=0.5
        )
        
        self.mp_draw = mp.solutions.drawing_utils

    def detect_intake(self, frame):
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. 손 검출
        hand_results = self.hands.process(rgb_frame)
        # 2. 얼굴 검출
        face_results = self.face_detection.process(rgb_frame)
        
        is_intake = False
        distance = 1.0 # 정규화된 거리 (최대 1)

        if hand_results.multi_hand_landmarks and face_results.detections:
            # 손가락 끝(검지: 8번) 좌표 가져오기
            hand_landmarks = hand_results.multi_hand_landmarks[0]
            finger_tip = hand_landmarks.landmark[8] 
            
            # 얼굴 중심 좌표(코 끝 근처) 가져오기
            face = face_results.detections[0]
            bbox = face.location_data.relative_bounding_box
            face_center_x = bbox.xmin + (bbox.width / 2)
            face_center_y = bbox.ymin + (bbox.height / 2)

            # 유클리드 거리 계산 (정규화된 좌표 기준)
            distance = np.sqrt((finger_tip.x - face_center_x)**2 + (finger_tip.y - face_center_y)**2)

            # 임계값 설정 (라파 테스트 후 조정 필요, 보통 0.1~0.15)
            if distance < 0.12:
                is_intake = True

        return is_intake, distance

    def release(self):
        self.hands.close()
        self.face_detection.close()