import RPi.GPIO as GPIO
import time
import sys
import os

# 프로젝트 루트 경로 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from config.settings import PAN_PIN, TILT_PIN

def test_servo(pin, label):
    print(f"\n--- Testing {label} (Pin {pin}) ---")
    try:
        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, 50) # 50Hz
        pwm.start(0)
        
        def set_angle(angle):
            duty = 2.5 + (angle / 180.0) * 10.0
            pwm.ChangeDutyCycle(duty)
            print(f"[{label}] Angle: {angle:3d}°, Duty: {duty:4.1f}%")
            time.sleep(0.3)

        print("1. Moving to 0-90-180-90...")
        for angle in [0, 90, 180, 90]:
            set_angle(angle)
            time.sleep(0.5)
        
        print("2. Sweeping (0 to 180)...")
        for a in range(0, 181, 10):
            set_angle(a)
        
        print("3. Manual Control (Enter angle 0-180, 'q' to next/quit)")
        while True:
            val = input(f"Enter angle for {label} (0-180) or 'q': ").strip().lower()
            if val == 'q':
                break
            try:
                angle = int(val)
                if 0 <= angle <= 180:
                    set_angle(angle)
                else:
                    print("Out of range (0-180)")
            except ValueError:
                print("Invalid input")
            
        pwm.stop()
        print(f"{label} test completed.")
    except Exception as e:
        print(f"Error testing {label}: {e}")

if __name__ == "__main__":
    if os.getuid() != 0:
        print("[WARN] Root 권한(sudo)이 아닐 경우 GPIO 작동이 제한될 수 있습니다.")
    
    print("CareFull Servo Motor Debug Tool")
    print("-------------------------------")
    print(f"Configured TILT_PIN: {TILT_PIN}")
    print(f"Configured PAN_PIN:  {PAN_PIN}")
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    try:
        test_servo(TILT_PIN, "TILT (Horizontal/X)")
        print("\n" + "="*30)
        test_servo(PAN_PIN, "PAN (Vertical/Y)")
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        GPIO.cleanup()
        print("\nGPIO cleaned up. Goodbye!")
