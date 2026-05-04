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
    1축 서보 모터 제어 (19번 핀 전용) - 정밀도 향상 및 데드존 최적화
    """
    def __init__(self):
        self.servo_pin = TILT_PIN  # 19번 핀
        self.angle = 90            # 초기 각도 (중앙)
        
        # 추적 파라미터 (사용자 피드백 반영)
        self.threshold = 30        # 데드존 설정 (사용자 제안 +-30)
        self.kP = 0.04             # 비례 계수 약간 하향 (더 부드러운 접근)
        self.min_step = 0.3        # 최소 동작 각도 하향 (정밀도 향상)
        
        # 평활화 설정
        self.smooth_error_x = 0
        self.alpha = 0.25          # 필터링 강화 (0.3 -> 0.25): 떨림 억제력 증대
        
        # GPIO 설정
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.servo_pin, 50)
            self.pwm.start(0)
            time.sleep(0.1)
            self.set_angle(self.angle)
            logger.info(f"Gimbal precision mode initialized. Deadzone: {self.threshold}")
        except Exception as e:
            logger.error(f"Gimbal GPIO Setup Error: {e}")

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """각도 설정 (0~180)"""
        try:
            target_angle = max(0, min(180, angle))
            
            # 0.1도 이하의 미세 변화는 무시 (디지털 서보의 떨림 방지)
            if abs(self.angle - target_angle) < 0.1:
                return

            self.angle = target_angle
            duty = self._angle_to_duty(self.angle)
            self.pwm.ChangeDutyCycle(duty)
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """사용자 제안 범위를 반영한 정밀 추적 로직"""
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        
        raw_error_x = face_center_x - frame_center_x
        
        # 1. 지수 이동 평균 필터
        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        # 2. 데드존 체크 (+-30 이내면 즉시 정지 및 필터 초기화)
        if abs(self.smooth_error_x) < self.threshold:
            # 타겟이 범위 안에 들어오면 오차 누적값을 현재 오차로 동기화하여 
            # 다음 번에 범위를 벗어날 때 급격하게 튀는 현상 방지
            self.smooth_error_x = raw_error_x 
            return

        # 3. 비례 제어 (P-Control)
        # 오차에서 데드존을 뺀 만큼만 이동하게 하여 경계선에서의 덜컥거림 완화
        effective_error = self.smooth_error_x - (self.threshold if self.smooth_error_x > 0 else -self.threshold)
        adjustment = effective_error * self.kP
        
        # 4. 최소 동작 각도 체크
        if abs(adjustment) < self.min_step:
            return
            
        # 5. 각도 업데이트
        self.set_angle(self.angle - adjustment)

    def reset(self):
        self.set_angle(90)

    def stop(self):
        self.pwm.stop()
        logger.info("Gimbal PWM stopped.")
