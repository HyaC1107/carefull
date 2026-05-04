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
    1축 서보 모터 제어 (19번 핀 전용) - 떨림 및 반동 제거 모드
    """
    def __init__(self):
        self.servo_pin = TILT_PIN
        self.angle = 90            # 현재 각도
        self.target_angle = 90     # 목표 각도
        self.reverse = GIMBAL_REVERSE
        
        # 떨림 방지 파라미터
        self.threshold = 70        # 데드존 확대 (중앙 부근 떨림 원천 차단)
        self.alpha = 0.1           # 매우 강력한 좌표 평활화
        self.smooth_error_x = 0
        
        # 반동 및 흔들림 제어
        self.step_size = 0.8       # 한 번 이동 시 보폭 (너무 크면 반동 생김)
        self.move_interval = 0.15  # 이동 간격 (물리적 진동이 가라앉을 시간)
        self.last_move_time = 0
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.servo_pin, GPIO.OUT)
            self.pwm = GPIO.PWM(self.servo_pin, 50)
            self.pwm.start(0)
            time.sleep(0.1)
            self.set_angle(self.angle)
            logger.info("Gimbal anti-vibration mode started.")
        except Exception as e:
            logger.error(f"Gimbal Setup Error: {e}")

    def _angle_to_duty(self, angle):
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        """각도 설정 후 즉시 신호 차단하여 떨림 방지"""
        try:
            self.angle = max(0, min(180, angle))
            duty = self._angle_to_duty(self.angle)
            
            # 1. 신호 전송
            self.pwm.ChangeDutyCycle(duty)
            # 2. 서보 이동 시간 (0.05초로 단축하여 반응성 향상)
            time.sleep(0.05)
            # 3. 신호 차단
            self.pwm.ChangeDutyCycle(0)
            
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """반동 및 급격한 튐 현상을 방지하는 로직"""
        now = time.time()
        
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        
        raw_error_x = face_center_x - frame_center_x
        
        # [추가] 좌표 점프 방지 (Outlier Rejection)
        # 이전 오차값과 현재 오차값의 차이가 너무 크면(화면의 1/3 이상) 무시
        if self.smooth_error_x != 0 and abs(raw_error_x - self.smooth_error_x) > (frame_w / 3):
            return

        # 1. 좌표 필터링
        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        # 2. 데드존 및 쿨다운 체크
        if abs(self.smooth_error_x) < self.threshold or (now - self.last_move_time < self.move_interval):
            return

        # 3. 목표 방향 결정 (기존 방향으로 원복)
        # 얼굴이 오른쪽(error > 0)이면 각도를 줄여서(-) 추적
        # 얼굴이 왼쪽(error < 0)이면 각도를 늘려서(+) 추적
        move_dir = -1 if not self.reverse else 1
        
        # 오차 크기에 따라 보폭 조절
        dynamic_step = self.step_size
        if abs(self.smooth_error_x) > 150:
            dynamic_step *= 2
            
        if self.smooth_error_x > 0:
            self.target_angle = self.angle + (dynamic_step * move_dir)
        else:
            self.target_angle = self.angle - (dynamic_step * move_dir)

        # 4. 단계 이동 실행
        self.set_angle(self.target_angle)
        self.last_move_time = now

    def move_cooldown(self):
        # 이동 중에는 쿨다운을 짧게, 정지 후에는 길게 가져가서 반동 억제
        return self.move_interval

    def reset(self):
        self.set_angle(90)

    def stop(self):
        self.pwm.ChangeDutyCycle(0)
        self.pwm.stop()
        logger.info("Gimbal PWM stopped.")
