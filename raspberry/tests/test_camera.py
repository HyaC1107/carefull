import sys
import os
import time
import cv2
import numpy as np

# MediaPipe는 라즈베리파이 환경에 따라 설치 여부가 다를 수 있으므로 예외 처리
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

# 상수 정의 (기존 settings.py 의존성 제거를 위해 직접 정의)
WIDTH = 640
HEIGHT = 480

class StandaloneCameraTester:
    def __init__(self):
        self._picam2 = None
        self._webcam = None
        self._face_detection = None
        
        if HAS_MEDIAPIPE:
            mp_face = mp.solutions.face_detection
            self._face_detection = mp_face.FaceDetection(
                model_selection=0, 
                min_detection_confidence=0.5
            )
            print("[INFO] MediaPipe Face Detection initialized.")
        else:
            print("[WARN] MediaPipe not found. Only Camera Feed will be shown.")

    def _init_camera(self):
        # 1. Picamera2 시도
        try:
            from picamera2 import Picamera2
            cam = Picamera2()
            cam.configure(cam.create_preview_configuration(
                main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
            ))
            cam.start()
            self._picam2 = cam
            print("[INFO] Picamera2 initialized successfully.")
            return True
        except Exception:
            # 2. USB 웹캠 폴백
            self._webcam = cv2.VideoCapture(0)
            self._webcam.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
            self._webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            if self._webcam.isOpened():
                print("[INFO] USB Webcam initialized successfully.")
                return True
        return False

    def get_frame(self):
        if self._picam2:
            frame = self._picam2.capture_array()
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        elif self._webcam:
            ok, frame = self._webcam.read()
            return frame if ok else None
        return None

    def detect_face(self, frame):
        if not self._face_detection or frame is None:
            return []
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_detection.process(rgb_frame)
        faces = []
        
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x = int(bbox.xmin * WIDTH)
                y = int(bbox.ymin * HEIGHT)
                w = int(bbox.width * WIDTH)
                h = int(bbox.height * HEIGHT)
                faces.append((x, y, w, h))
        return faces

    def draw_debug(self, frame, faces):
        # 화면 중앙 가이드선 (Blue)
        cx, cy = WIDTH // 2, HEIGHT // 2
        cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (255, 0, 0), 2)
        cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (255, 0, 0), 2)
        
        if faces:
            # 가장 큰 얼굴 기준
            faces.sort(key=lambda f: f[2] * f[3], reverse=True)
            x, y, w, h = faces[0]
            fx, fy = x + w // 2, y + h // 2
            
            # 얼굴 박스 및 중심점 (Green)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.circle(frame, (fx, fy), 6, (0, 0, 255), -1)
            
            # 오차 거리 및 선 표시
            error_x = fx - cx
            cv2.line(frame, (cx, cy), (fx, fy), (0, 255, 255), 2)
            
            # 정보 텍스트
            cv2.putText(frame, f"Face Center: ({fx}, {fy})", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Offset X: {error_x}", (20, 70), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            cv2.putText(frame, "No Face Detected", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
        return frame

    def run(self):
        if not self._init_camera():
            print("[ERROR] Could not open any camera.")
            return

        print("\n--- Camera & Face Visual Test Start ---")
        print("Press 'q' to exit.")
        
        try:
            while True:
                frame = self.get_frame()
                if frame is None:
                    continue
                
                faces = self.detect_face(frame)
                frame = self.draw_debug(frame, faces)
                
                cv2.imshow("CareFull Visual Camera Test", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            if self._picam2: self._picam2.stop()
            if self._webcam: self._webcam.release()
            cv2.destroyAllWindows()
            print("--- Test Finished ---")

if __name__ == "__main__":
    tester = StandaloneCameraTester()
    tester.run()
