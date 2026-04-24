import RPi.GPIO as GPIO
import time
import sys

# 사용할 GPIO 핀 번호 (BCM 방식)
GPIO_PINS = [12, 16, 20, 21]

# 28BYJ-48 스텝 시퀀스 (8단계 방식, 더 부드럽게 움직임)
STEP_SEQ = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

def setup():
    GPIO.setmode(GPIO.BCM)
    for pin in GPIO_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, False)

def rotate(steps):
    # steps가 양수면 정방향, 음수면 역방향
    direction = 1 if steps > 0 else -1
    steps = abs(steps)
    
    step_count = len(STEP_SEQ)
    
    for i in range(steps):
        for pin_idx in range(4):
            # 시퀀스에 맞춰 핀 신호 전송
            GPIO.output(GPIO_PINS[pin_idx], STEP_SEQ[i % step_count][pin_idx] if direction == 1 
                        else STEP_SEQ[(step_count - 1 - (i % step_count))][pin_idx])
        time.sleep(0.001) # 속도 조절 (너무 빠르면 모터가 못 따라옴)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python3 motor.py [스텝수]")
        print("예: python3 motor.py 512 (약 45도 회전)")
        sys.exit()

    try:
        input_steps = int(sys.argv[1])
        setup()
        print(f"{input_steps} 스텝만큼 회전 시작!")
        rotate(input_steps)
        print("회전 완료!")
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup() # GPIO 설정 초기화