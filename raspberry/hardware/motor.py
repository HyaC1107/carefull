import time
import logging

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

from config.settings import STEP_PINS, PUMP_PIN

logger = logging.getLogger("Motor")

# 스텝 모터 시퀀스 (8단계)
STEP_SEQ = [
    [1, 0, 0, 0], [1, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0],
    [0, 0, 1, 0], [0, 0, 1, 1], [0, 0, 0, 1], [1, 0, 0, 1]
]

def dispense_medicine(user=None):
    """
    약 디스펜싱 수행
    개선: 지글링(Jiggle) 패턴 및 가감속(Ramping) 적용
    1. 스텝 모터 회전 (약 배출 - 지글링 적용)
    2. 펌프 모터 가동 (물 배출)
    """
    logger.info(f"Dispensing medicine for user: {user} with Jiggle pattern")
    
    try:
        # 1. 스텝 모터 회전 (-256단계)
        # 지글링 패턴 적용: 흔들면서 전진하여 끼임 방지
        _run_step_motor_with_jiggle(total_steps=-256, chunk_size=64, jiggle_steps=12, delay=0.005)
        
        # 2. 펌프 모터 제어
        _run_pump_motor(duration=2)
        
        logger.info("Dispensing completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Dispensing failed: {e}")
        return False

def _run_step_motor_with_jiggle(total_steps, chunk_size=64, jiggle_steps=10, delay=0.005):
    """
    흔들면서 전진하는 로직
    - total_steps: 최종 도달 목표 (예: -256)
    - chunk_size: 흔들기 주기가 되는 스텝 수
    - jiggle_steps: 역회전할 스텝 수 (끼임 방지 진동 효과)
    """
    direction = 1 if total_steps > 0 else -1
    remaining_steps = abs(total_steps)
    
    logger.info(f"Starting Jiggle movement: Total {total_steps} steps")
    
    while remaining_steps > 0:
        # 이번에 전진할 크기
        current_chunk = min(remaining_steps, chunk_size)
        
        # 1. 정방향 전진
        _run_step_motor(current_chunk * direction, delay)
        remaining_steps -= current_chunk
        
        # 2. 끼임 방지를 위한 역방향 살짝 후진 (마지막 구간이 아닐 때만)
        if remaining_steps > 0:
            time.sleep(0.05) # 짧은 휴지기 (관성 제거)
            _run_step_motor(jiggle_steps * -direction, delay) # 역회전 (흔들기)
            time.sleep(0.05)
            _run_step_motor(jiggle_steps * direction, delay)  # 다시 원위치로 복귀
            time.sleep(0.05)
            
    logger.debug("Jiggle movement completed.")

def _run_step_motor(steps, delay=0.001):
    """
    스텝 모터 구동 로직 (가감속/Ramping 적용)
    """
    direction = 1 if steps > 0 else -1
    steps = abs(steps)
    step_count = len(STEP_SEQ)

    logger.debug(f"Rotating step motor: {steps} steps (dir: {direction})")
    for i in range(steps):
        # 가감속(Ramping): 시작과 끝 15스텝은 속도를 1.5배 느리게 하여 토크 확보 및 오버런 방지
        current_delay = delay
        if i < 15 or i > (steps - 15):
            current_delay = delay * 1.5
            
        for pin_idx in range(4):
            seq_idx = i % step_count
            if direction == -1:
                seq_idx = (step_count - 1) - seq_idx
            
            GPIO.output(STEP_PINS[pin_idx], STEP_SEQ[seq_idx][pin_idx])
        time.sleep(current_delay)
    
    # 정지 후 전류 차단 (발열 방지)
    for pin in STEP_PINS:
        GPIO.output(pin, False)

def _run_pump_motor(duration):
    """펌프 모터 구동 로직"""
    logger.info(f"Running pump motor for {duration} seconds...")
    try:
        GPIO.setup(PUMP_PIN, GPIO.OUT)
        GPIO.output(PUMP_PIN, True)
        time.sleep(duration)
        GPIO.output(PUMP_PIN, False)
        logger.info("Pump motor stopped.")
    except Exception as e:
        logger.error(f"Pump motor control failed: {e}")
