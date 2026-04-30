import logging
import time

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

from config.settings import PAN_PIN, TILT_PIN

logger = logging.getLogger("Gimbal")

class Gimbal:
    """
    2축(Pan, Tilt) 서보 모터를 제어하여 얼굴을 추적하는 클래스
    SG90 서보 모터 기준 (50Hz, Duty Cycle 2.5~12.5)
    
    [모터 구성]
    1. Pan (좌우): 카메라를 수평 방향으로 회전시킴 (PAN_PIN: 13)
    2. Tilt (상하): 카메라를 수직 방향으로 회전시킴 (TILT_PIN: 19)
    """
    def __init__(self):
        self.pan_pin = PAN_PIN    # 좌우 회전용 GPIO 핀
        self.tilt_pin = TILT_PIN  # 상하 회전용 GPIO 핀
        
        # 초기 각도 (중앙 90도 정렬)
        self.pan_angle = 90
        self.tilt_angle = 90
        
        # GPIO 설정 (이미 메인에서 setmode가 되었다고 가정하지만 안전을 위해)
        # GPIO.setmode(GPIO.BCM) 
        GPIO.setup(self.pan_pin, GPIO.OUT)
        GPIO.setup(self.tilt_pin, GPIO.OUT)
        
        # PWM 설정 (50Hz)
        self.pan_pwm = GPIO.PWM(self.pan_pin, 50)
        self.tilt_pwm = GPIO.PWM(self.tilt_pin, 50)
        
        self.pan_pwm.start(self._angle_to_duty(self.pan_angle))
        self.tilt_pwm.start(self._angle_to_duty(self.tilt_angle))
        
        logger.info(f"Gimbal initialized on Pins: Pan={self.pan_pin}, Tilt={self.tilt_pin}")

    def _angle_to_duty(self, angle):
        """각도(0~180)를 Duty Cycle(2.5~12.5)로 변환"""
        return 2.5 + (angle / 180.0) * 10.0

    def set_angles(self, pan, tilt):
        """
        Pan(좌우), Tilt(상하) 각도 직접 설정
        pan: 0(왼쪽) ~ 180(오른쪽)
        tilt: 0(아래) ~ 180(위)
        """
        self.pan_angle = max(0, min(180, pan))
        self.tilt_angle = max(0, min(180, tilt))
        
        self.pan_pwm.ChangeDutyCycle(self._angle_to_duty(self.pan_angle))
        self.tilt_pwm.ChangeDutyCycle(self._angle_to_duty(self.tilt_angle))

    def track_face(self, face_bbox, frame_w, frame_h):
        """
        얼굴 위치에 따라 짐벌 각도 조정
        face_bbox: (x, y, w, h)
        """
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        face_center_y = y + h / 2
        
        frame_center_x = frame_w / 2
        frame_center_y = frame_h / 2
        
        error_x = face_center_x - frame_center_x
        error_y = face_center_y - frame_center_y
        
        # 데드존 (불필요한 미세 떨림 방지)
        self.threshold = 40 
        
        # 이동 단계 (각도 크기 하향 조정: 1.5 -> 0.8, 1.0 -> 0.5)
        self.pan_step = 0.8
        self.tilt_step = 0.5
        
        new_pan = self.pan_angle
        new_tilt = self.tilt_angle
        
        # Pan 조정 (좌우 회전)
        if abs(error_x) > self.threshold:
            if error_x > 0:
                new_pan -= self.pan_step
            else:
                new_pan += self.pan_step
                
        # Tilt 조정 (상하 회전)
        if abs(error_y) > self.threshold:
            if error_y > 0:
                new_tilt += self.tilt_step
            else:
                new_tilt -= self.tilt_step
                
        self.set_angles(new_pan, new_tilt)

    def reset(self):
        """중앙 정렬"""
        self.set_angles(90, 90)

    def stop(self):
        """PWM 정지"""
        self.pan_pwm.stop()
        self.tilt_pwm.stop()
        logger.info("Gimbal PWM stopped.")
