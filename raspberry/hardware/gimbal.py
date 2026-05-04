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
    1축 서보 모터 제어 (19번 핀 전용) - 진동 완전 해결 및 딜레이 로직 적용
    """
    def __init__(self):
        self.servo_pin = TILT_PIN  # 19번 핀
        self.angle = 90            # 초기 각도 (중앙)
        
        # 추적 및 안정화 파라미터
        self.threshold = 50        # 데드존 대폭 확대 (사용자 요청: +-50)
        self.kP = 0.03             # 비례 계수 (안정적인 추적을 위해 유지)
        self.min_step = 0.5        # 최소 동작 각도 (미세 떨림 방지)
        
        # 움직임 간 딜레이(쿨다운) 설정
        self.last_move_time = 0
        self.move_cooldown = 0.1   # 0.1초 동안은 다음 움직임 대기 (안정감 향상)
        
        # 필터링 설정
        self.smooth_error_x = 0
        self.alpha = 0.2           # 필터링 강화
        
        # GPIO 설정
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.servo_pin, 50)
            self.pwm.start(0)
            time.sleep(0.1)
            self.set_angle(self.angle)
            logger.info(f"Gimbal stability mode: Deadzone={self.threshold}, Cooldown={self.move_cooldown}s")
        except Exception as e:
            logger.error(f"Gimbal GPIO Setup Error: {e}")

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """각도 설정 (0~180) 및 PWM 신호 관리"""
        try:
            target_angle = max(0, min(180, angle))
            
            # 변화가 적으면 신호를 차단하여 진동 방지
            if abs(self.angle - target_angle) < 0.3:
                self.pwm.ChangeDutyCycle(0)
                return

            self.angle = target_angle
            duty = self._angle_to_duty(self.angle)
            self.pwm.ChangeDutyCycle(duty)
            
            # 신호가 전달될 최소 시간을 보장하기 위해 짧은 지연을 줄 수도 있으나
            # 여기서는 호출 주기(face_thread의 msleep)에 맡깁니다.
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """딜레이와 데드존을 활용한 안정적인 추적"""
        now = time.time()
        
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        
        raw_error_x = face_center_x - frame_center_x
        
        # 1. 지수 이동 평균 필터
        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        # 2. 데드존 체크 (+-50픽셀 이내면 PWM 신호 즉시 차단)
        if abs(self.smooth_error_x) < self.threshold:
            self.pwm.ChangeDutyCycle(0) # 신호 차단 (진동 해결의 핵심)
            self.smooth_error_x = raw_error_x
            return

        # 3. 움직임 간 딜레이(쿨다운) 체크
        if now - self.last_move_time < self.move_cooldown:
            # 쿨다운 중에는 신호만 차단하고 대기
            self.pwm.ChangeDutyCycle(0)
            return

        # 4. 비례 제어 (P-Control)
        effective_error = self.smooth_error_x - (self.threshold if self.smooth_error_x > 0 else -self.threshold)
        adjustment = effective_error * self.kP
        
        # 5. 최소 동작 각도 체크
        if abs(adjustment) < self.min_step:
            self.pwm.ChangeDutyCycle(0)
            return
            
        # 6. 각도 업데이트 및 시간 기록
        self.set_angle(self.angle - adjustment)
        self.last_move_time = now

    def reset(self):
        self.set_angle(90)

    def stop(self):
        self.pwm.stop()
        logger.info("Gimbal PWM stopped.")
