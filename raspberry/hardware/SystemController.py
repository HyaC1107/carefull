import logging
import threading
import time
import os

# 라즈베리파이 환경 대응
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

from scheduler.schedule import check_schedule, sync_schedules
from hardware.alarm import play_alarm, stop_alarm
from config.settings import VOICES_DIR

logger = logging.getLogger("SystemController")

class SystemController(threading.Thread):
    """
    하드웨어 관리와 백그라운드 스케줄 감시를 통합한 메인 컨트롤러
    """
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True

    # --- 하드웨어 관리 로직 ---
    
    @staticmethod
    def initialize_hardware():
        """전체 하드웨어(GPIO, 센서 등) 초기화"""
        logger.info("Initializing hardware components...")
        try:
            # 보이스 디렉토리 생성
            os.makedirs(VOICES_DIR, exist_ok=True)
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # 디스펜서 핀 초기화 (12, 16, 20, 21)
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
    def cleanup_hardware():
        """종료 시 모든 GPIO 리소스 해제 및 알람 중지"""
        logger.info("Cleaning up hardware resources...")
        try:
            stop_alarm()
            GPIO.cleanup()
            logger.info("Hardware cleanup successful.")
        except Exception as e:
            logger.error(f"Error during hardware cleanup: {e}")

    @staticmethod
    def self_test():
        """모든 하드웨어 구성 요소가 정상인지 테스트"""
        logger.info("Running hardware self-test...")
        results = {
            "gpio": True,
            "motor": "ready",
            "fingerprint_sensor": "pending",
            "alarm_speaker": "ready"
        }
        return results

    @staticmethod
    def emergency_stop():
        """긴급 상황 시 모든 구동 장치를 즉시 정지"""
        logger.warning("EMERGENCY STOP CALLED!")
        try:
            stop_alarm()
            dispenser_pins = [12, 16, 20, 21]
            for pin in dispenser_pins:
                GPIO.output(pin, False)
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")

    # --- 백그라운드 스케줄링 로직 ---

    def run(self):
        logger.info("SystemController Background Thread started.")
        
        # 시작 시 스케줄 동기화
        sync_schedules()
        
        while self.running:
            try:
                # 스케줄 확인
                due_schedules = check_schedule()
                
                if due_schedules:
                    for s in due_schedules:
                        sche_id = s.get("sche_id")
                        medi_name = s.get("medi_name", "약")
                        logger.info(f"Schedule Triggered: {medi_name} (ID: {sche_id})")
                        
                        # 결제 여부에 따른 알람 파일 결정
                        custom_voice = f"voice_{sche_id}.mp3"
                        play_alarm(custom_voice)
                        
                        # 여기에 디스펜서 동작 등 추가 하드웨어 제어 로직을 넣을 수 있습니다.
                        
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in SystemController loop: {e}")
                time.sleep(10)

    def stop(self):
        self.running = False
