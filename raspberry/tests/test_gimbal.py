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
    """
    hardware/gimbal.py에 의존하지 않는 독립형 테스트용 짐벌 클래스
    핀 번호: Pan=13, Tilt=19 고정
    """
    def __init__(self):
        self.pan_pin = PAN_PIN   # 13
        self.tilt_pin = TILT_PIN # 19
        self.pan_angle = 90
        self.tilt_angle = 90
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pan_pin, GPIO.OUT)
        GPIO.setup(self.tilt_pin, GPIO.OUT)
        
        self.pan_pwm = GPIO.PWM(self.pan_pin, 50)
        self.tilt_pwm = GPIO.PWM(self.tilt_pin, 50)
        
        self.pan_pwm.start(self._angle_to_duty(self.pan_angle))
        self.tilt_pwm.start(self._angle_to_duty(self.tilt_angle))
        
        # 테스트용 부드러운 이동 설정 (더 천천히!)
        self.threshold = 50      # 데드존을 넓혀서 불필요한 떨림 방지
        self.pan_step = 0.3      # 한 번에 움직이는 각도를 매우 작게 (0.7 -> 0.3)
        self.tilt_step = 0.2     # (0.4 -> 0.2)

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

def test_gimbal_movement_standalone():
    """독립형 미세 가동 테스트 (매우 천천히)"""
    logger.info("--- [독립형] 짐벌 미세 가동 테스트 시작 ---")
    gimbal = StandaloneGimbal()
    try:
        p, t = gimbal.pan_angle, gimbal.tilt_angle
        # 1도씩 아주 천천히 확인
        for i in range(10):
            gimbal.set_angles(p + i, t)
            time.sleep(0.5) # 0.2 -> 0.5초로 대기 시간 증가
        for i in range(10, -11, -1):
            gimbal.set_angles(p + i, t)
            time.sleep(0.5)
        gimbal.set_angles(p, t)
        logger.info("테스트 완료")
    finally:
        gimbal.stop()

def test_gimbal_tracking_standalone():
    """독립형 실시간 추적 테스트 (부드럽게)"""
    logger.info("--- [독립형] 실시간 얼굴 추적 테스트 시작 ---")
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
                cv2.rectangle(frame, (x,y), (x+w,y+h), (255,0,0), 2)
            
            cv2.putText(frame, f"PAN: {gimbal.pan_angle:.1f} TILT: {gimbal.tilt_angle:.1f}", 
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.imshow("Standalone Gimbal Test", frame)
            
            # 루프 사이클에 아주 짧은 휴식을 주어 추적 속도를 조절
            time.sleep(0.05)
            
            if cv2.waitKey(1) & 0xFF == ord('q'): break
    finally:
        cv2.destroyAllWindows()
        release_camera()
        gimbal.stop()

if __name__ == "__main__":
    print("1. 독립형 미세 가동 테스트")
    print("2. 독립형 실시간 추적 테스트")
    c = input("선택: ")
    if c == '1': test_gimbal_movement_standalone()
    elif c == '2': test_gimbal_tracking_standalone()
    GPIO.cleanup()
