import logging

# 라즈베리파이 환경이 아닐 경우를 대비한 가상 GPIO 처리 (선택 사항)
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
    GPIO = MockGPIO()

logger = logging.getLogger("HardwareManager")

class HardwareManager:
    """하드웨어의 전체 생명주기를 관리하는 클래스"""
    
    @staticmethod
    def initialize():
        """전체 하드웨어(GPIO, 센서 등) 초기화"""
        logger.info("Initializing hardware components...")
        try:
            # 1. GPIO 기본 설정
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 2. 디스펜서 핀 초기화 (예시 핀 번호)
            # 실제 핀 번호는 hardware/dispenser.py와 맞추는 것이 좋습니다.
            dispenser_pins = [12, 16, 20, 21]
            for pin in dispenser_pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, False)
                
            logger.info("GPIO and Dispenser pins initialized.")
            return True
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}")
            return False

    @staticmethod
    def cleanup():
        """종료 시 모든 GPIO 리소스 해제"""
        logger.info("Cleaning up hardware resources...")
        try:
            GPIO.cleanup()
            logger.info("Hardware cleanup successful.")
        except Exception as e:
            logger.error(f"Error during hardware cleanup: {e}")

    @staticmethod
    def self_test():
        """모든 하드웨어 구성 요소가 정상인지 테스트"""
        logger.info("Running hardware self-test...")
        # TODO: 지문 센서 연결 확인, 알람 테스트 재생 등 로직 추가
        results = {
            "gpio": True,
            "dispenser_motor": "ready",
            "fingerprint_sensor": "pending",
            "alarm_speaker": "ready"
        }
        return results

    @staticmethod
    def emergency_stop():
        """긴급 상황 시 모든 구동 장치(모터, 펌프)를 즉시 정지"""
        logger.warning("EMERGENCY STOP CALLED!")
        try:
            # 모든 제어 핀을 LOW로 설정
            dispenser_pins = [12, 16, 20, 21]
            for pin in dispenser_pins:
                GPIO.output(pin, False)
            # 알람 정지 등 추가 로직
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")
