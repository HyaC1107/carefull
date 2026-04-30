import sys
import os
import time
import logging
import cv2

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

from camera.camera import get_frame, release_camera
from face_detection.mediapipe_detector import detect_face
from config.settings import CAMERA_WIDTH, CAMERA_HEIGHT, TILT_PIN

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("GimbalTest")

class StandaloneGimbal:
    def __init__(self):
        self.servo_pin = TILT_PIN # 19
        self.angle = 90
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.servo_pin, 50)
        self.pwm.start(self._angle_to_duty(self.angle))
        
        self.threshold = 40
        self.step = 1.0

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        self.angle = max(0, min(180, angle))
        self.pwm.ChangeDutyCycle(self._angle_to_duty(self.angle))

    def track_face(self, face_bbox, frame_w, frame_h):
        x, y, w, h = face_bbox
        error_x = (x + w/2) - (frame_w / 2)
        
        new_angle = self.angle
        if abs(error_x) > self.threshold:
            new_angle += self.step if error_x < 0 else -self.step
        self.set_angle(new_angle)
        return error_x

    def stop(self):
        self.pwm.stop()

def _draw_debug_info(frame, gimbal, face_bbox=None):
    """얼굴 인식 및 중심점 정보를 화면에 그림"""
    # 1. 화면 중앙 조준선 (Blue)
    cx, cy = CAMERA_WIDTH // 2, CAMERA_HEIGHT // 2
    cv2.line(frame, (cx - 20, cy), (cx + 20, cy), (255, 0, 0), 2)
    cv2.line(frame, (cx, cy - 20), (cx, cy + 20), (255, 0, 0), 2)
    cv2.circle(frame, (cx, cy), gimbal.threshold, (255, 0, 0), 1) # 데드존 표시
    
    error_x = 0
    if face_bbox:
        x, y, w, h = face_bbox
        fx, fy = x + w // 2, y + h // 2
        error_x = fx - cx
        
        # 2. 얼굴 박스 및 중심점 (Green/Red)
        color = (0, 255, 0) if abs(error_x) <= gimbal.threshold else (0, 0, 255)
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.circle(frame, (fx, fy), 5, (0, 0, 255), -1) # 얼굴 중심점
        
        # 3. 연결선 (얼굴 중심 <-> 화면 중심)
        cv2.line(frame, (cx, cy), (fx, fy), (0, 255, 255), 1)
        
    # 4. 상태 텍스트
    status_color = (0, 255, 0) if abs(error_x) <= gimbal.threshold else (0, 165, 255)
    cv2.putText(frame, f"Angle: {gimbal.angle:.1f}", (20, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Error X: {error_x:.1f}", (20, 70), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    
    return frame

def test_single_axis_movement():
    logger.info("--- 19번 핀 가동 범위 테스트 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        for angle in range(90, -1, -5):
            gimbal.set_angle(angle)
            frame = get_frame()
            if frame is not None:
                frame = _draw_debug_info(frame, gimbal)
                cv2.imshow("Gimbal Visual Test", frame)
                cv2.waitKey(1)
            time.sleep(0.05)
        for angle in range(0, 181, 5):
            gimbal.set_angle(angle)
            frame = get_frame()
            if frame is not None:
                frame = _draw_debug_info(frame, gimbal)
                cv2.imshow("Gimbal Visual Test", frame)
                cv2.waitKey(1)
            time.sleep(0.05)
        gimbal.set_angle(90)
        logger.info("테스트 완료. 'q'를 눌러 종료하세요.")
        while cv2.waitKey(1) & 0xFF != ord('q'): pass
    finally:
        cv2.destroyAllWindows()
        gimbal.stop()
        release_camera()

def test_single_axis_tracking():
    logger.info("--- 19번 핀 실시간 시각화 추적 테스트 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        while True:
            frame = get_frame()
            if frame is None: continue
            
            faces = detect_face(frame)
            main_face = None
            if faces:
                faces.sort(key=lambda x: x[2]*x[3], reverse=True)
                main_face = faces[0]
                gimbal.track_face(main_face, CAMERA_WIDTH, CAMERA_HEIGHT)
            
            frame = _draw_debug_info(frame, gimbal, main_face)
            cv2.imshow("Gimbal Visual Tracking", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): break
    finally:
        cv2.destroyAllWindows()
        release_camera()
        gimbal.stop()

if __name__ == "__main__":
    print("========================================")
    print("   Visual Gimbal Test (Pin 19 Only)    ")
    print("========================================")
    print("1. 가동 범위 테스트 (중심선 확인)")
    print("2. 실시간 추적 테스트 (얼굴 중심점 확인)")
    print("q. 종료")
    
    choice = input("\n선택: ")
    if choice == '1': test_single_axis_movement()
    elif choice == '2': test_single_axis_tracking()
    
    if GPIO:
        GPIO.cleanup()
