import RPi.GPIO as GPIO
import time
import sys  # 명령줄 인수를 받기 위해 필요해!

GPIO_PINS = [12, 16, 20, 21]
STEP_SEQ = [
    [1, 0, 0, 0], [1, 1, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0],
    [0, 0, 1, 0], [0, 0, 1, 1], [0, 0, 0, 1], [1, 0, 0, 1]
]

def stepmotor(steps, delay=0.001):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in GPIO_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, False)

    direction = 1 if steps > 0 else -1
    steps = abs(steps)
    step_count = len(STEP_SEQ)

    try:
        for i in range(steps):
            for pin_idx in range(4):
                seq_idx = i % step_count
                if direction == -1:
                    seq_idx = (step_count - 1) - seq_idx
                
                GPIO.output(GPIO_PINS[pin_idx], STEP_SEQ[seq_idx][pin_idx])
            time.sleep(delay)
    finally:
        for pin in GPIO_PINS:
            GPIO.output(pin, False)

# --- 직접 실행을 위한 코드 
# --- Main에서 불러와 쓸땐 필요없음
if __name__ == "__main__":
    # 터미널에서 인자를 주었는지 확인 (예: python3 stepmotor.py 256)
    if len(sys.argv) > 1:
        try:
            input_steps = int(sys.argv[1])
            print(f"{input_steps} 스텝 회전 시작!")
            stepmotor(input_steps)
            print("회전 완료!")
            GPIO.cleanup()
        except ValueError:
            print("숫자를 입력해주세요.")
    else:
        print("사용법: python3 stepmotor.py [스텝수]")