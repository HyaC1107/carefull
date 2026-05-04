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

from config.settings import TILT_PIN # 19번 핀 사용

logger = logging.getLogger("Gimbal")

class Gimbal:
    """
    1축 서보 모터 제어 (19번 핀 전용)
    """
    def __init__(self):
        self.servo_pin = TILT_PIN  # 19번 핀
        self.angle = 90            # 초기 각도 (중앙)
        
        # 추적 설정 (이 값이 없으면 track_face에서 에러 발생)
        self.threshold = 40        # 데드존 (픽셀)
        self.step = 1.0            # 이동 크기 (도)
        
        # GPIO 설정 보강
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.servo_pin, 50)
            self.pwm.start(0) # 일단 신호 없이 시작
            time.sleep(0.1)
            self.set_angle(self.angle)
            logger.info(f"Gimbal initialized on Pin: {self.servo_pin}")
        except Exception as e:
            logger.error(f"Gimbal GPIO Setup Error: {e}")

    def _angle_to_duty(self, angle):
        # 0도: 2.5, 90도: 7.5, 180도: 12.5 (일반적인 50Hz 서보)
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """각도 설정 (0~180)"""
        try:
            self.angle = max(0, min(180, angle))
            duty = self._angle_to_duty(self.angle)
            self.pwm.ChangeDutyCycle(duty)
            # 하드웨어 PWM이 아닐 경우 너무 빠른 연속 호출은 무시될 수 있으므로
            # 상위 루프에서 제어하거나 필요시 짧은 sleep을 줄 수 있음
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """얼굴의 좌우 위치(x)에 따라 19번 핀 모터 제어"""
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        
        error_x = face_center_x - frame_center_x
        
        new_angle = self.angle
        
        if abs(error_x) > self.threshold:
            # 얼굴이 중앙보다 오른쪽에 있으면(error_x > 0) 각도를 줄여서 오른쪽으로 회전
            if error_x > 0:
                new_angle -= self.step
            else:
                new_angle += self.step
                
        self.set_angle(new_angle)

    def reset(self):
        self.set_angle(90)

    def stop(self):
        self.pwm.stop()
        logger.info("Gimbal PWM stopped.")
