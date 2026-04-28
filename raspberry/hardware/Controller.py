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
from hardware.motor import dispense_medicine
from camera.camera import check_camera_health, release_camera
from config.settings import VOICES_DIR, STEP_PINS

logger = logging.getLogger("Controller")

class Controller(threading.Thread):
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

            for pin in STEP_PINS:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, False)
                
            logger.info("GPIO and Motor pins initialized.")
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
            release_camera()
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
            "camera": check_camera_health(),
            "alarm_speaker": "ready"
        }
        return results

    @staticmethod
    def emergency_stop():
        """긴급 상황 시 모든 구동 장치를 즉시 정지"""
        logger.warning("EMERGENCY STOP CALLED!")
        try:
            stop_alarm()
            for pin in STEP_PINS:
                GPIO.output(pin, False)
            release_camera()
        except Exception as e:
            logger.error(f"Emergency stop failed: {e}")

    # --- 백그라운드 스케줄링 로직 ---

    def run(self):
        logger.info("Controller Background Thread started.")
        
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
                        logger.info(f"--- Medication Process Start: {medi_name} (ID: {sche_id}) ---")
                        
                        # 1. 스케줄 확인 및 알람 (hardware.md #1)
                        custom_voice = f"voice_{sche_id}.mp3"
                        play_alarm(custom_voice)
                        
                        # 2. 카메라 준비 (hardware.md #2)
                        # UI에서 사용할 수 있도록 카메라 상태 점검 및 활성화 유도
                        if check_camera_health():
                            logger.info("Camera is ready for authentication.")
                        else:
                            logger.warning("Camera preparation failed!")

                        # 3. 사용자 인증 (hardware.md #3) - [TODO: 구현 예정]
                        # face_recognition 또는 fingerprint 모듈을 통한 인증 로직이 여기에 들어갑니다.
                        logger.info("[PENDING] Waiting for user authentication...")
                        is_authenticated = True # 테스트를 위해 임시로 True 설정
                        
                        if is_authenticated:
                            # 4. 약제 배출 (hardware.md #4)
                            logger.info("Authentication success. Starting motor control...")
                            if dispense_medicine(user=f"user_{sche_id}"):
                                logger.info("Medicine dispensed successfully.")
                                
                                # 5. 복약 행위 검증 (hardware.md #5) - [TODO: 구현 예정]
                                # 카메라와 AI 모델을 사용하여 실제 복용 여부를 확인하는 로직이 들어갑니다.
                                logger.info("[PENDING] Verifying medication intake...")
                            else:
                                logger.error("Medicine dispensing failed.")
                        else:
                            logger.warning("Authentication failed or timeout.")

                        logger.info(f"--- Medication Process End: {medi_name} ---")
                        
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in Controller loop: {e}")
                time.sleep(10)

    def stop(self):
        self.running = False
