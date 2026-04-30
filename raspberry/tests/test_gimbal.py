import sys
import os
import time
import logging
import cv2

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

from hardware.gimbal import Gimbal
from camera.camera import get_frame, release_camera
from face_detection.mediapipe_detector import detect_face
from config.settings import CAMERA_WIDTH, CAMERA_HEIGHT

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("GimbalTest")

def init_gpio():
    if GPIO:
        try:
            mode = GPIO.getmode()
            if mode is None:
                GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
        except Exception as e:
            logger.error(f"GPIO 초기화 실패: {e}")
    else:
        logger.warning("RPi.GPIO 모듈을 찾을 수 없습니다. Mock 모드로 동작합니다.")

def test_gimbal_movement_small():
    """현재 위치 기준 아주 작은 범위(+/- 20도)만 천천히 테스트"""
    init_gpio()
    gimbal = Gimbal()
    logger.info("--- 짐벌 미세 가동 테스트 시작 (현재 위치 기준) ---")
    
    try:
        current_pan = gimbal.pan_angle
        current_tilt = gimbal.tilt_angle
        
        # Pan 미세 테스트 (+/- 20도, 2도씩 천천히)
        logger.info(f"Pan 미세 테스트 시작 (현재: {current_pan})")
        for angle in range(int(current_pan), int(current_pan + 21), 2):
            gimbal.set_angles(angle, current_tilt)
            time.sleep(0.3)
        for angle in range(int(current_pan + 20), int(current_pan - 21), -2):
            gimbal.set_angles(angle, current_tilt)
            time.sleep(0.3)
        gimbal.set_angles(current_pan, current_tilt)
        
        time.sleep(1)
        
        # Tilt 미세 테스트 (+/- 15도, 2도씩 천천히)
        logger.info(f"Tilt 미세 테스트 시작 (현재: {current_tilt})")
        for angle in range(int(current_tilt), int(current_tilt + 16), 2):
            gimbal.set_angles(current_pan, angle)
            time.sleep(0.3)
        for angle in range(int(current_tilt + 15), int(current_tilt - 16), -2):
            gimbal.set_angles(current_pan, angle)
            time.sleep(0.3)
        gimbal.set_angles(current_pan, current_tilt)
            
        logger.info("짐벌 미세 가동 테스트 완료")
    except Exception as e:
        logger.error(f"짐벌 테스트 중 오류 발생: {e}")
    finally:
        gimbal.stop()

def test_gimbal_face_tracking_smooth():
    """정렬 없이 현재 위치에서 부드럽게 추적 시작"""
    init_gpio()
    gimbal = Gimbal()
    logger.info("--- 부드러운 실시간 얼굴 추적 테스트 시작 ---")
    logger.info("종료하려면 카메라 창에서 'q'를 누르세요.")
    
    try:
        # 초기 정렬(reset) 생략 - 현재 위치에서 바로 시작
        while True:
            frame = get_frame()
            if frame is None:
                continue
            
            faces = detect_face(frame)
            if faces:
                faces.sort(key=lambda x: x[2] * x[3], reverse=True)
                main_face = faces[0]
                
                # gimbal.py 내부에서 조정된 작은 스텝값으로 추적
                gimbal.track_face(main_face, CAMERA_WIDTH, CAMERA_HEIGHT)
                
                x, y, w, h = main_face
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # 안내선 및 상태 표시
            cv2.line(frame, (CAMERA_WIDTH // 2, 0), (CAMERA_WIDTH // 2, CAMERA_HEIGHT), (255, 0, 0), 1)
            cv2.line(frame, (0, CAMERA_HEIGHT // 2), (CAMERA_WIDTH, CAMERA_HEIGHT // 2), (255, 0, 0), 1)
            cv2.putText(frame, f"P: {gimbal.pan_angle:.1f}, T: {gimbal.tilt_angle:.1f}", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("Gimbal Smooth Tracking Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        logger.error(f"얼굴 추적 테스트 중 오류 발생: {e}")
    finally:
        cv2.destroyAllWindows()
        release_camera()
        gimbal.stop()

if __name__ == "__main__":
    try:
        print("========================================")
        print("   CareFull Gimbal Smooth Test Tool     ")
        print("========================================")
        print("1. 짐벌 미세 가동 테스트 (현재 기준 +/- 20도)")
        print("2. 부드러운 얼굴 추적 테스트 (정렬 없음)")
        print("q. 종료")
        
        while True:
            choice = input("\n원하는 테스트 번호를 입력하세요: ")
            
            if choice == '1':
                test_gimbal_movement_small()
            elif choice == '2':
                test_gimbal_face_tracking_smooth()
            elif choice == 'q':
                break
            else:
                print("잘못된 입력입니다.")
    finally:
        if GPIO:
            GPIO.cleanup()
