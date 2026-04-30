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
from config.settings import CAMERA_WIDTH, CAMERA_HEIGHT, PAN_PIN, TILT_PIN

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("GimbalTest")

class StandaloneGimbal:
    def __init__(self):
        self.pan_pin = PAN_PIN
        self.tilt_pin = TILT_PIN
        self.pan_angle = 90
        self.tilt_angle = 90
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pan_pin, GPIO.OUT)
        GPIO.setup(self.tilt_pin, GPIO.OUT)
        
        self.pan_pwm = GPIO.PWM(self.pan_pin, 50)
        self.tilt_pwm = GPIO.PWM(self.tilt_pin, 50)
        
        self.pan_pwm.start(self._angle_to_duty(self.pan_angle))
        self.tilt_pwm.start(self._angle_to_duty(self.tilt_angle))
        
        self.threshold = 35
        self.pan_step = 1.2
        self.tilt_step = 0.8

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angles(self, pan, tilt):
        self.pan_angle = max(0, min(180, pan))
        self.tilt_angle = max(0, min(180, tilt))
        self.pan_pwm.ChangeDutyCycle(self._angle_to_duty(self.pan_angle))
        self.tilt_pwm.ChangeDutyCycle(self._angle_to_duty(self.tilt_angle))

    def track_face(self, face_bbox, frame_w, frame_h):
        x, y, w, h = face_bbox
        error_x = (x + w/2) - (frame_w / 2)
        error_y = (y + h/2) - (frame_h / 2)
        
        new_pan = self.pan_angle
        new_tilt = self.tilt_angle
        
        if abs(error_x) > self.threshold:
            new_pan += self.pan_step if error_x < 0 else -self.pan_step
                
        if abs(error_y) > self.threshold:
            new_tilt -= self.tilt_step if error_y < 0 else self.tilt_step
                
        self.set_angles(new_pan, new_tilt)

    def stop(self):
        self.pan_pwm.stop()
        self.tilt_pwm.stop()

def _show_frame_with_info(gimbal, title="Gimbal Test"):
    """화면을 가져와서 현재 각도 정보를 입혀서 보여줌"""
    frame = get_frame()
    if frame is not None:
        cv2.line(frame, (CAMERA_WIDTH//2, 0), (CAMERA_WIDTH//2, CAMERA_HEIGHT), (255,0,0), 1)
        cv2.line(frame, (0, CAMERA_HEIGHT//2), (CAMERA_WIDTH, CAMERA_HEIGHT//2), (255,0,0), 1)
        cv2.putText(frame, f"PAN: {gimbal.pan_angle:.1f} TILT: {gimbal.tilt_angle:.1f}", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow(title, frame)
        cv2.waitKey(1)
    return frame

def test_gimbal_movement_general():
    """일반 가동 범위 테스트 (화면 동시 출력)"""
    logger.info("--- [일반] 짐벌 가동 테스트 및 화면 출력 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        # Pan 테스트
        logger.info("Pan 테스트 중 (화면 확인)...")
        for angle in range(90, -1, -5):
            gimbal.set_angles(angle, 90)
            _show_frame_with_info(gimbal, "Movement Test")
            time.sleep(0.02)
        for angle in range(0, 181, 5):
            gimbal.set_angles(angle, 90)
            _show_frame_with_info(gimbal, "Movement Test")
            time.sleep(0.02)
        gimbal.set_angles(90, 90)
        
        # Tilt 테스트
        logger.info("Tilt 테스트 중 (화면 확인)...")
        for angle in range(90, -1, -5):
            gimbal.set_angles(90, angle)
            _show_frame_with_info(gimbal, "Movement Test")
            time.sleep(0.02)
        for angle in range(0, 181, 5):
            gimbal.set_angles(90, angle)
            _show_frame_with_info(gimbal, "Movement Test")
            time.sleep(0.02)
        gimbal.set_angles(90, 90)
        
        logger.info("테스트 완료 (창을 닫으려면 'q' 또는 아무 키나 누르세요)")
        cv2.waitKey(0) # 결과 화면 잠시 유지
    finally:
        cv2.destroyAllWindows()
        gimbal.stop()
        release_camera()

def test_gimbal_tracking_general():
    """일반 실시간 추적 테스트"""
    logger.info("--- [일반] 실시간 얼굴 추적 테스트 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        gimbal.set_angles(90, 90)
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
            cv2.line(frame, (0, CAMERA_HEIGHT//2), (CAMERA_WIDTH, CAMERA_HEIGHT//2), (255,0,0), 1)
            cv2.putText(frame, f"PAN: {gimbal.pan_angle:.1f} TILT: {gimbal.tilt_angle:.1f}", 
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow("Tracking Test", frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): break
    finally:
        cv2.destroyAllWindows()
        release_camera()
        gimbal.stop()

if __name__ == "__main__":
    print("1. 일반 가동 범위 테스트 (화면 포함)")
    print("2. 일반 실시간 추적 테스트")
    print("q. 종료")
    
    choice = input("\n선택: ")
    if choice == '1': test_gimbal_movement_general()
    elif choice == '2': test_gimbal_tracking_general()
    
    if GPIO:
        GPIO.cleanup()
