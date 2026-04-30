import sys
import os
import time
import logging

# 프로젝트 루트 경로 추가 (부모 디렉토리의 부모)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hardware.motor import dispense_medicine, _run_step_motor, _run_pump_motor
from config.settings import STEP_PINS, PUMP_PIN

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("MotorTest")

def init_gpio():
    """테스트를 위한 GPIO 초기화"""
    if GPIO:
        try:
            # 이미 모드가 설정되어 있는지 확인 (오류 방지)
            mode = GPIO.getmode()
            if mode is None:
                logger.info("GPIO 모드 설정 중 (BCM)...")
                GPIO.setmode(GPIO.BCM)
            
            GPIO.setwarnings(False)
            
            # 핀 설정
            for pin in STEP_PINS:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, False)
            if PUMP_PIN:
                GPIO.setup(PUMP_PIN, GPIO.OUT)
                GPIO.output(PUMP_PIN, False)
        except Exception as e:
            logger.error(f"GPIO 초기화 실패: {e}")
    else:
        logger.warning("RPi.GPIO 모듈을 찾을 수 없습니다. Mock 모드로 동작합니다.")

def test_stepper_motor():
    """스텝 모터 단독 테스트 (회전 확인)"""
    init_gpio()
    logger.info("--- 스텝 모터 테스트 시작 (512 steps) ---")
    try:
        # 512단계 회전 테스트
        _run_step_motor(512, delay=0.002)
        logger.info("스텝 모터 테스트 완료")
    except Exception as e:
        logger.error(f"스텝 모터 테스트 실패: {e}")

def test_pump_motor():
    """펌프 모터 단독 테스트"""
    init_gpio()
    logger.info("--- 펌프 모터 테스트 시작 (3 seconds) ---")
    try:
        _run_pump_motor(3)
        logger.info("펌프 모터 테스트 완료 (로그 확인)")
    except Exception as e:
        logger.error(f"펌프 모터 테스트 실패: {e}")

def test_full_dispense():
    """전체 디스펜싱 시퀀스 테스트"""
    init_gpio()
    logger.info("--- 전체 디스펜싱 시퀀스 테스트 시작 ---")
    try:
        success = dispense_medicine(user="TestUser")
        if success:
            logger.info("전체 디스펜싱 시퀀스 테스트 완료")
        else:
            logger.error("전체 디스펜싱 시퀀스 테스트 실패")
    except Exception as e:
        logger.error(f"전체 시퀀스 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    try:
        print("========================================")
        print("   CareFull Motor Hardware Test Tool    ")
        print("========================================")
        print("1. 스텝 모터 개별 테스트 (약 배출)")
        print("2. 펌프 모터 개별 테스트 (물/보조)")
        print("3. 전체 디스펜싱 시퀀스 실행")
        print("q. 종료")
        
        while True:
            choice = input("\n원하는 테스트 번호를 입력하세요: ")
            
            if choice == '1':
                test_stepper_motor()
            elif choice == '2':
                test_pump_motor()
            elif choice == '3':
                test_full_dispense()
            elif choice == 'q':
                print("테스트를 종료합니다.")
                break
            else:
                print("잘못된 입력입니다.")
    finally:
        if GPIO:
            logger.info("GPIO 리소스 정리 중...")
            GPIO.cleanup()
