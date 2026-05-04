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
    1축 서보 모터 제어 (19번 핀 전용) - 진동 방지 및 부드러운 추적 적용
    """
    def __init__(self):
        self.servo_pin = TILT_PIN  # 19번 핀
        self.angle = 90            # 초기 각도 (중앙)
        
        # 추적 파라미터 최적화
        self.threshold = 60        # 데드존 확대 (기존 40 -> 60): 너무 작은 움직임 무시
        self.kP = 0.05             # 비례 제어 계수: 오차에 비례하여 속도 조절
        self.min_step = 0.5        # 최소 이동 각도: 이보다 작으면 움직이지 않음 (진동 방지)
        
        # 부드러운 제어를 위한 이전 값 보관 (지수 이동 평균용)
        self.smooth_error_x = 0
        self.alpha = 0.3           # 평활화 계수 (0~1): 낮을수록 부드럽지만 느려짐
        
        # GPIO 설정
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.servo_pin, 50)
            self.pwm.start(0)
            time.sleep(0.1)
            self.set_angle(self.angle)
            logger.info(f"Gimbal initialized with smoothing on Pin: {self.servo_pin}")
        except Exception as e:
            logger.error(f"Gimbal GPIO Setup Error: {e}")

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """각도 설정 (0~180)"""
        try:
            target_angle = max(0, min(180, angle))
            
            # 이전 각도와 차이가 거의 없으면 하드웨어 신호를 보내지 않음 (미세 떨림 방지)
            if abs(self.angle - target_angle) < 0.2:
                return

            self.angle = target_angle
            duty = self._angle_to_duty(self.angle)
            self.pwm.ChangeDutyCycle(duty)
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """얼굴 위치에 따라 부드럽게 추적"""
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        
        raw_error_x = face_center_x - frame_center_x
        
        # 1. 지수 이동 평균을 통한 오차 평활화 (Jitter 제거)
        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        # 2. 데드존 체크
        if abs(self.smooth_error_x) < self.threshold:
            return

        # 3. 비례 제어 (P-Control): 멀수록 크게, 가까울수록 작게 이동
        adjustment = self.smooth_error_x * self.kP
        
        # 4. 최소 이동 제한 (미세 진동 방지)
        if abs(adjustment) < self.min_step:
            return
            
        # 5. 각도 업데이트 (부호 주의: 화면상 얼굴이 오른쪽(error > 0)이면 카메라는 오른쪽(각도 감소)으로)
        self.set_angle(self.angle - adjustment)

    def reset(self):
        self.set_angle(90)

    def stop(self):
        self.pwm.stop()
        logger.info("Gimbal PWM stopped.")
