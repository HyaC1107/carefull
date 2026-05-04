import logging
import time

try:
    import pigpio
except ImportError:
    class MockPigpio:
        def pi(self): return self
        def set_mode(self, pin, mode): pass
        def set_servo_pulsewidth(self, pin, width): pass
        def stop(self): pass
        OUTPUT = 1
    pigpio = MockPigpio()

from config.settings import TILT_PIN, GIMBAL_REVERSE

logger = logging.getLogger("Gimbal")

class Gimbal:
    """
    1축 서보 모터 제어 (19번 핀) - pigpio 하드웨어 PWM 기반 정밀 제어
    """
    def __init__(self):
        self.servo_pin = TILT_PIN
        self.angle = 90
        self.reverse = GIMBAL_REVERSE
        
        # [제어 파라미터]
        self.threshold = 70        # 데드존 (중앙 부근 안정성)
        self.alpha = 0.1           # 필터링 (인식 좌표 떨림 방지)
        self.smooth_error_x = 0
        self.step_size = 0.8       # 기본 이동 보폭
        self.move_interval = 0.05  # 최소 이동 간격 (s)
        self.last_move_time = 0
        
        # [상태 관리 파ar미터]
        self.last_face_time = time.time()
        self.idle_timeout = 2.0    # 미감지 시 복귀 시간 (s)
        self.is_resetting = False
        
        # pigpio 초기화
        self.pi = pigpio.pi()
        if not self.pi.connected:
            logger.error("pigpiod 데몬이 실행 중이지 않습니다. 'sudo pigpiod'를 실행하세요.")
        else:
            self.pi.set_mode(self.servo_pin, pigpio.OUTPUT)
            self.set_angle(self.angle)
            logger.info("Gimbal (pigpio) initialized successfully.")

    def _angle_to_pulsewidth(self, angle):
        """각도(0~180)를 마이크로초(500~2500)로 변환"""
        return 500 + (angle / 180.0) * 2000

    def set_angle(self, angle):
        """하드웨어 PWM 신호를 이용한 각도 설정"""
        if not self.pi.connected: return
        try:
            self.angle = max(0, min(180, angle))
            pulsewidth = self._angle_to_pulsewidth(self.angle)
            self.pi.set_servo_pulsewidth(self.servo_pin, pulsewidth)
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """부드러운 추적 및 상태 업데이트"""
        now = time.time()
        self.last_face_time = now 
        self.is_resetting = False
        
        x, y, w, h = face_bbox
        raw_error_x = (x + w / 2) - (frame_w / 2)
        
        # 1. Outlier Rejection (급격한 좌표 튐 방지)
        if self.smooth_error_x != 0 and abs(raw_error_x - self.smooth_error_x) > (frame_w / 3):
            return

        # 2. Smoothing
        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        # 3. Deadzone & Interval Check
        if abs(self.smooth_error_x) < self.threshold or (now - self.last_move_time < self.move_interval):
            return

        # 4. Direction & Step (이전 안정 버전 로직 유지)
        move_dir = -1 if not self.reverse else 1
        dynamic_step = self.step_size
        if abs(self.smooth_error_x) > 150: dynamic_step *= 2
            
        target = self.angle + (dynamic_step * move_dir if self.smooth_error_x > 0 else -dynamic_step * move_dir)
        
        self.set_angle(target)
        self.last_move_time = now

    def update_idle(self):
        """미감지 시 정위치 복귀 로직"""
        now = time.time()
        if not self.is_resetting and (now - self.last_face_time > self.idle_timeout):
            if abs(self.angle - 90) > 1.0:
                self.set_angle(90)
            self.is_resetting = True
            logger.info("Idle timeout reached. Returning to center.")
        
        # 정지 상태에서 신호 차단하여 떨림/발열 방지
        if self.is_resetting or abs((self.angle - 90)) < 0.1:
            self.pi.set_servo_pulsewidth(self.servo_pin, 0)

    def stop(self):
        """종료 및 리소스 해제"""
        if self.pi.connected:
            self.pi.set_servo_pulsewidth(self.servo_pin, 0)
            self.pi.stop()
        logger.info("Gimbal resources released.")
