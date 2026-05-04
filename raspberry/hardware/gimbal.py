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
    1축 서보 모터 제어 (19번 핀) - pigpio 하드웨어 PWM 버전
    """
    def __init__(self):
        self.servo_pin = TILT_PIN
        self.angle = 90
        self.reverse = GIMBAL_REVERSE
        
        # [사용자 최적화 파라미터 유지]
        self.threshold = 30        
        self.alpha = 0.1           
        self.smooth_error_x = 0
        self.step_size = 0.8       
        self.move_interval = 0.05  
        self.last_move_time = 0
        
        # pigpio 초기화
        self.pi = pigpio.pi()
        if not self.pi.connected:
            logger.error("pigpiod 데몬이 실행 중이지 않습니다. 'sudo pigpiod'를 실행하세요.")
        else:
            self.pi.set_mode(self.servo_pin, pigpio.OUTPUT)
            self.set_angle(self.angle)
            logger.info("Gimbal hardware PWM (pigpio) started.")

    def _angle_to_pulsewidth(self, angle):
        """
        각도를 펄스 폭(500~2500)으로 변환
        0도: 500, 90도: 1500, 180도: 2500
        """
        return 500 + (angle / 180.0) * 2000

    def set_angle(self, angle):
        """하드웨어 PWM으로 각도 설정 (떨림 없음)"""
        if not self.pi.connected: return
        
        try:
            self.angle = max(0, min(180, angle))
            pulsewidth = self._angle_to_pulsewidth(self.angle)
            
            # pigpio는 하드웨어 타이밍이므로 신호를 계속 줘도 떨림이 거의 없지만,
            # 서보 모터 보호를 위해 이동 후 신호를 끊는 옵션을 유지하거나 선택할 수 있습니다.
            self.pi.set_servo_pulsewidth(self.servo_pin, pulsewidth)
            
            # 이동 후 전력 차단이 필요하다면 아래 주석 해제 (단, 힘이 빠져서 고정력이 약해질 수 있음)
            # time.sleep(0.1)
            # self.pi.set_servo_pulsewidth(self.servo_pin, 0)
            
        except Exception as e:
            logger.error(f"Gimbal set_angle Error: {e}")

    def track_face(self, face_bbox, frame_w, frame_h):
        """기존 최적화 로직 그대로 사용"""
        now = time.time()
        x, y, w, h = face_bbox
        face_center_x = x + w / 2
        frame_center_x = frame_w / 2
        raw_error_x = face_center_x - frame_center_x
        
        # 좌표 점프 방지
        if self.smooth_error_x != 0 and abs(raw_error_x - self.smooth_error_x) > (frame_w / 3):
            return

        self.smooth_error_x = (self.alpha * raw_error_x) + ((1 - self.alpha) * self.smooth_error_x)
        
        if abs(self.smooth_error_x) < self.threshold or (now - self.last_move_time < self.move_interval):
            return

        move_dir = -1 if not self.reverse else 1
        dynamic_step = self.step_size
        if abs(self.smooth_error_x) > 150:
            dynamic_step *= 2
            
        if self.smooth_error_x > 0:
            target = self.angle + (dynamic_step * move_dir)
        else:
            target = self.angle - (dynamic_step * move_dir)

        self.set_angle(target)
        self.last_move_time = now

    def reset(self):
        self.set_angle(90)

    def stop(self):
        """종료 시 신호 차단"""
        if self.pi.connected:
            self.pi.set_servo_pulsewidth(self.servo_pin, 0)
            self.pi.stop()
        logger.info("Gimbal pigpio stopped.")
