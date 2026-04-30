import sys
import os
import time
import cv2
import numpy as np

# 프로젝트 루트 경로 추가 (기본 설정 로드를 위해)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# GPIO 라이브러리 예외 처리
try:
    import RPi.GPIO as GPIO
except ImportError:
    class MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        def setmode(self, mode): pass
        def setwarnings(self, flag): pass
        def setup(self, pin, mode): pass
        def output(self, pin, state): pass
        def cleanup(self): pass
        class PWM:
            def __init__(self, pin, freq): pass
            def start(self, dc): pass
            def ChangeDutyCycle(self, dc): pass
            def stop(self): pass
    GPIO = MockGPIO()

# MediaPipe 예외 처리
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

# 필수 설정값 직접 정의 (의존성 최소화)
WIDTH = 640
HEIGHT = 480
SERVO_PIN = 19  # 사용자의 요청에 따른 19번 핀 고정

class FinalStandaloneGimbalTester:
    def __init__(self):
        # 1. 카메라 및 인식기 설정
        self._picam2 = None
        self._webcam = None
        self._face_detection = None
        
        # 2. 서보 모터 설정
        self.angle = 90
        self.threshold = 40  # 데드존
        self.step = 1.0      # 이동 크기
        
        # 3. GPIO 초기화
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SERVO_PIN, GPIO.OUT)
        self.pwm = GPIO.PWM(SERVO_PIN, 50)
        self.pwm.start(self._angle_to_duty(self.angle))
        
        # 4. 얼굴 인식기 초기화
        if HAS_MEDIAPIPE:
            mp_face = mp.solutions.face_detection
            self._face_detection = mp_face.FaceDetection(
                model_selection=0, 
                min_detection_confidence=0.5
            )
            print("[INFO] MediaPipe Face Detection initialized.")

    # --- 서보 제어 로직 ---
    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        self.angle = max(0, min(180, angle))
        self.pwm.ChangeDutyCycle(self._angle_to_duty(self.angle))

    def track_face_logic(self, face_bbox):
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = WIDTH / 2
        error_x = face_center_x - frame_center_x
        
        new_angle = self.angle
        if abs(error_x) > self.threshold:
            # 얼굴이 중앙보다 오른쪽에 있으면(error_x > 0) 각도를 줄여서 오른쪽으로 회전
            if error_x > 0:
                new_angle -= self.step
            else:
                new_angle += self.step
        self.set_angle(new_angle)
        return error_x

    # --- 카메라 로직 (test_camera.py 방식 통합) ---
    def _init_camera(self):
        try:
            from picamera2 import Picamera2
            cam = Picamera2()
            cam.configure(cam.create_preview_configuration(
                main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
            ))
            cam.start()
            self._picam2 = cam
            print("[INFO] Picamera2 initialized.")
            return True
        except Exception:
            self._webcam = cv2.VideoCapture(0)
            self._webcam.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
            self._webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
            if self._webcam.isOpened():
                print("[INFO] USB Webcam initialized.")
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

    def detect_faces(self, frame):
        if not self._face_detection or frame is None:
            return []
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_detection.process(rgb_frame)
        faces = []
        if results.detections:
            for detection in results.detections:
                bbox = detection.location_data.relative_bounding_box
                x, y, w, h = int(bbox.xmin*WIDTH), int(bbox.ymin*HEIGHT), int(bbox.width*WIDTH), int(bbox.height*HEIGHT)
                faces.append((x, y, w, h))
        return faces

    # --- 시각화 로직 ---
    def draw_visuals(self, frame, faces, error_x):
        # 중앙 가이드라인
        cx, cy = WIDTH // 2, HEIGHT // 2
        cv2.line(frame, (cx, 0), (cx, HEIGHT), (255, 0, 0), 1)
        cv2.circle(frame, (cx, cy), self.threshold, (255, 0, 0), 1)
        
        if faces:
            faces.sort(key=lambda f: f[2]*f[3], reverse=True)
            x, y, w, h = faces[0]
            fx = x + w // 2
            
            # 얼굴 박스 및 중심점
            color = (0, 255, 0) if abs(error_x) <= self.threshold else (0, 0, 255)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.circle(frame, (fx, y + h // 2), 5, (0, 0, 255), -1)
            cv2.line(frame, (cx, cy), (fx, y + h // 2), (0, 255, 255), 2)

        # 정보 텍스트 표시
        cv2.putText(frame, f"Angle: {self.angle:.1f}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Error X: {error_x:.1f}", (20, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        return frame

    def run_tracking_test(self):
        if not self._init_camera():
            print("[ERROR] Camera failed.")
            return

        print("\n--- Standalone Gimbal Tracking Test Start ---")
        print("Press 'q' to exit.")
        
        try:
            while True:
                frame = self.get_frame()
                if frame is None: continue
                
                faces = self.detect_faces(frame)
                error_x = 0
                if faces:
                    faces.sort(key=lambda f: f[2]*f[3], reverse=True)
                    error_x = self.track_face_logic(faces[0])
                
                frame = self.draw_visuals(frame, faces, error_x)
                cv2.imshow("Standalone Gimbal Tracking", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.pwm.stop()
            if self._picam2: self._picam2.stop()
            if self._webcam: self._webcam.release()
            cv2.destroyAllWindows()
            GPIO.cleanup()
            print("--- Test Finished ---")

    def run_movement_test(self):
        """19번 핀 가동 범위 테스트 (0~180도)"""
        if not self._init_camera(): return
        print("\n--- Gimbal Range Test (0 -> 180) ---")
        try:
            for angle in range(90, -1, -5):
                self.set_angle(angle)
                frame = self.get_frame()
                if frame is not None:
                    frame = self.draw_visuals(frame, [], 0)
                    cv2.imshow("Standalone Gimbal Range Test", frame)
                cv2.waitKey(1)
                time.sleep(0.05)
            for angle in range(0, 181, 5):
                self.set_angle(angle)
                frame = self.get_frame()
                if frame is not None:
                    frame = self.draw_visuals(frame, [], 0)
                    cv2.imshow("Standalone Gimbal Range Test", frame)
                cv2.waitKey(1)
                time.sleep(0.05)
            self.set_angle(90)
            print("Range test complete. Press any key on window to finish.")
            cv2.waitKey(0)
        finally:
            self.pwm.stop()
            if self._picam2: self._picam2.stop()
            if self._webcam: self._webcam.release()
            cv2.destroyAllWindows()
            GPIO.cleanup()

if __name__ == "__main__":
    tester = FinalStandaloneGimbalTester()
    print("1. 짐벌 가동 범위 테스트 (0~180도)")
    print("2. 실시간 얼굴 추적 테스트 (카메라 화면 포함)")
    choice = input("선택: ")
    
    if choice == '1': tester.run_movement_test()
    elif choice == '2': tester.run_tracking_test()
