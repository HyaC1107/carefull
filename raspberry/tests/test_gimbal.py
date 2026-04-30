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
    """독립형 1축 테스트 클래스 (19번 핀 전용)"""
    def __init__(self):
        self.servo_pin = TILT_PIN # 19
        self.angle = 90
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.servo_pin, 50)
        self.pwm.start(self._angle_to_duty(self.angle))
        
        self.threshold = 35
        self.step = 1.2

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        self.angle = max(0, min(180, angle))
        self.pwm.ChangeDutyCycle(self._angle_to_duty(self.angle))

    def track_face(self, face_bbox, frame_w, frame_h):
        """좌우(x) 위치로 19번 핀 제어"""
        x, y, w, h = face_bbox
        error_x = (x + w/2) - (frame_w / 2)
        
        new_angle = self.angle
        if abs(error_x) > self.threshold:
            new_angle += self.step if error_x < 0 else -self.step
        self.set_angle(new_angle)

    def stop(self):
        self.pwm.stop()

def _show_frame_with_info(gimbal, title="Single Axis Test"):
    frame = get_frame()
    if frame is not None:
        cv2.line(frame, (CAMERA_WIDTH//2, 0), (CAMERA_WIDTH//2, CAMERA_HEIGHT), (255,0,0), 1)
        cv2.putText(frame, f"SERVO(Pin19) Angle: {gimbal.angle:.1f}", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(title, frame)
        cv2.waitKey(1)
    return frame

def test_single_axis_movement():
    """19번 핀 가동 범위 테스트 (화면 포함)"""
    logger.info("--- 19번 핀 가동 범위 테스트 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        for angle in range(90, -1, -5):
            gimbal.set_angle(angle)
            _show_frame_with_info(gimbal, "Movement Test")
            time.sleep(0.05)
        for angle in range(0, 181, 5):
            gimbal.set_angle(angle)
            _show_frame_with_info(gimbal, "Movement Test")
            time.sleep(0.05)
        gimbal.set_angle(90)
        logger.info("테스트 완료. 'q'를 누르세요.")
        while cv2.waitKey(1) & 0xFF != ord('q'): pass
    finally:
        cv2.destroyAllWindows()
        gimbal.stop()
        release_camera()

def test_single_axis_tracking():
    """19번 핀 좌우 얼굴 추적 테스트"""
    logger.info("--- 19번 핀 실시간 좌우 추적 테스트 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        while True:
            frame = get_frame()
            if frame is None: continue
            
            faces = detect_face(frame)
            if faces:
                faces.sort(key=lambda x: x[2]*x[3], reverse=True)
                gimbal.track_face(faces[0], CAMERA_WIDTH, CAMERA_HEIGHT)
                x,y,w,h = faces[0]
                cv2.rectangle(frame, (x,y), (x+w,y+h), (0, 255, 0), 2)
            
            cv2.line(frame, (CAMERA_WIDTH//2, 0), (CAMERA_WIDTH//2, CAMERA_HEIGHT), (255,0,0), 1)
            cv2.putText(frame, f"SERVO(Pin19) Angle: {gimbal.angle:.1f}", 
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow("Tracking Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): break
    finally:
        cv2.destroyAllWindows()
        release_camera()
        gimbal.stop()

if __name__ == "__main__":
    print("========================================")
    print("   Pin 19 Single Axis Gimbal Test      ")
    print("========================================")
    print("1. 19번 핀 가동 범위 테스트 (화면 포함)")
    print("2. 19번 핀 좌우 얼굴 추적 테스트")
    print("q. 종료")
    
    choice = input("\n선택: ")
    if choice == '1': test_single_axis_movement()
    elif choice == '2': test_single_axis_tracking()
    
    if GPIO:
        GPIO.cleanup()
