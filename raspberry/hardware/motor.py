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
    1. 스텝 모터 회전 (약 배출)
    2. 펌프 모터 가동 (물 배출)
    """
    logger.info(f"Dispensing medicine for user: {user}")
    
    try:
        # 1. 스텝 모터 회전 (-256단계)
        _run_step_motor(steps=-256, delay=0.005)
        
        # 2. 펌프 모터 제어
        _run_pump_motor(duration=2)
        
        logger.info("Dispensing completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Dispensing failed: {e}")
        return False

def _run_step_motor(steps, delay=0.001):
    """스텝 모터 구동 로직"""
    direction = 1 if steps > 0 else -1
    steps = abs(steps)
    step_count = len(STEP_SEQ)

    logger.debug(f"Rotating step motor: {steps} steps")
    for i in range(steps):
        for pin_idx in range(4):
            seq_idx = i % step_count
            if direction == -1:
                seq_idx = (step_count - 1) - seq_idx
            
            GPIO.output(STEP_PINS[pin_idx], STEP_SEQ[seq_idx][pin_idx])
        time.sleep(delay)
    
    # 정지 후 전류 차단
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

# ── 테스트 호환성을 위한 지글링 함수 (테스트 코드 유지용) ──────────────

def _run_step_motor_with_jiggle(total_steps, chunk_size=64, jiggle_steps=10, delay=0.005):
    """
    흔들면서 전진하는 로직 (테스트용)
    """
    direction = 1 if total_steps > 0 else -1
    remaining_steps = abs(total_steps)
    
    while remaining_steps > 0:
        current_chunk = min(remaining_steps, chunk_size)
        _run_step_motor(current_chunk * direction, delay)
        remaining_steps -= current_chunk
        
        if remaining_steps > 0:
            time.sleep(0.05)
            _run_step_motor(jiggle_steps * -direction, delay)
            time.sleep(0.05)
            _run_step_motor(jiggle_steps * direction, delay)
            time.sleep(0.05)
