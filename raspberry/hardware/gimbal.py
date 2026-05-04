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

from config.settings import TILT_PIN, GIMBAL_REVERSE

logger = logging.getLogger("Gimbal")

class Gimbal:
    """
    1축 서보 모터 제어 (19번 핀 전용) - 초정밀/저속 추적 모드
    """
    def __init__(self):
        self.servo_pin = TILT_PIN  # 19번 핀
        self.angle = 90            # 초기 각도 (중앙)
        self.reverse = GIMBAL_REVERSE
        
        # 추적 및 안정화 파라미터 (초정밀 튜닝)
        self.threshold = 60        # 데드존 확대 (+-60): 중앙 근처에서 확실히 멈춤
        self.kP = 0.1             # 비례 계수 낮춤: 부드럽게 접근
        self.min_step = 1        # 최소 동작 각도 낮춤: 정밀한 최종 위치 조정
        self.max_change = 2.0      # 프레임당 최대 회전 제한 (1.0도): '탁' 튀는 현상 원천 차단
        
        # 움직임 주기 설정 (빠른 업데이트 + 작은 보폭 = 부드러움)
        self.last_move_time = 0
        self.move_cooldown = 0.1  # 0.1초마다 업데이트 
        
        # 필터링 설정 (강력한 평활화)
        self.smooth_error_x = 0
        self.alpha = 0.1           # 필터링 대폭 강화 (0.1): 인식 좌표 흔들림 완전 무시
        
        # GPIO 설정
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.servo_pin, 50)
            self.pwm.start(0)
            time.sleep(0.5)
            self.set_angle(self.angle)
            logger.info(f"Gimbal precision crawl mode initialized. Reverse: {self.reverse}")
        except Exception as e:
            logger.error(f"Gimbal GPIO Setup Error: {e}")

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """각도 설정 (0~180) 및 PWM 신호 관리"""
        try:
            target_angle = max(0, min(180, angle))
            
            # 미세한 변화(0.1도)는 무시하여 소음 방지
            if abs(self.angle - target_angle) < 0.1:
                self.pwm.ChangeDutyCycle(0)
                return

            self.angle = target_angle
            duty = self._angle_to_duty(self.angle)
            self.pwm.ChangeDutyCycle(duty)
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """부드럽게 '기어가는' 추적 로직"""
        now = time.time()
        
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        
        raw_error_x = face_center_x - frame_center_x
        
        # 1. 지수 이동 평균 필터 (매우 부드러움)
        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        # 2. 데드존 체크
        if abs(self.smooth_error_x) < self.threshold:
            self.pwm.ChangeDutyCycle(0)
            self.smooth_error_x = raw_error_x
            return

        # 3. 움직임 쿨다운 체크 (0.05s)
        if now - self.last_move_time < self.move_cooldown:
            return

        # 4. 비례 제어 (P-Control)
        effective_error = self.smooth_error_x - (self.threshold if self.smooth_error_x > 0 else -self.threshold)
        adjustment = effective_error * self.kP
        
        # 5. 프레임당 최대 회전 각도 제한 (Snap 방지)
        if abs(adjustment) > self.max_change:
            adjustment = self.max_change if adjustment > 0 else -self.max_change
        
        # 6. 최소 동작 각도 체크
        if abs(adjustment) < self.min_step:
            self.pwm.ChangeDutyCycle(0)
            return
            
        # 7. 각도 업데이트 (방향 반전 설정 적용)
        move_dir = -1 if not self.reverse else 1
        self.set_angle(self.angle + (adjustment * move_dir))
        self.last_move_time = now

    def reset(self):
        self.set_angle(90)

    def stop(self):
        self.pwm.stop()
        logger.info("Gimbal PWM stopped.")
