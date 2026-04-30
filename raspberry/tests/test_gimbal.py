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

def test_gimbal_movement():
    """짐벌의 기본 가동 범위를 확인하는 테스트 (Pan 0~180, Tilt 0~180)"""
    init_gpio()
    gimbal = Gimbal()
    logger.info("--- 짐벌 가동 범위 테스트 시작 ---")
    
    try:
        # 중앙 정렬
        logger.info("중앙 정렬 (90, 90)")
        gimbal.reset()
        time.sleep(1)
        
        # Pan 테스트
        logger.info("Pan 테스트: 0 -> 180")
        for angle in range(90, -1, -10):
            gimbal.set_angles(angle, 90)
            time.sleep(0.2)
        for angle in range(0, 181, 10):
            gimbal.set_angles(angle, 90)
            time.sleep(0.2)
        
        # gimbal.reset()
        # time.sleep(1)
        
        # # Tilt 테스트
        # logger.info("Tilt 테스트: 0 -> 180")
        # for angle in range(90, -1, -10):
        #     gimbal.set_angles(90, angle)
        #     time.sleep(0.2)
        # for angle in range(0, 181, 10):
        #     gimbal.set_angles(90, angle)
        #     time.sleep(0.2)
            
        gimbal.reset()
        logger.info("짐벌 가동 테스트 완료")
    except Exception as e:
        logger.error(f"짐벌 테스트 중 오류 발생: {e}")
    finally:
        gimbal.stop()

def test_gimbal_face_tracking():
    """카메라와 얼굴 인식을 연동한 실시간 짐벌 추적 테스트"""
    init_gpio()
    gimbal = Gimbal()
    logger.info("--- 실시간 얼굴 추적 테스트 시작 ---")
    logger.info("종료하려면 카메라 창에서 'q'를 누르세요.")
    
    try:
        gimbal.reset()
        
        while True:
            frame = get_frame()
            if frame is None:
                logger.warning("프레임을 가져올 수 없습니다.")
                continue
            
            # 얼굴 인식
            faces = detect_face(frame)
            
            if faces:
                # 가장 큰 얼굴 하나만 추적
                faces.sort(key=lambda x: x[2] * x[3], reverse=True)
                main_face = faces[0]
                
                # 짐벌 추적 로직 실행
                gimbal.track_face(main_face, CAMERA_WIDTH, CAMERA_HEIGHT)
                
                # 얼굴 박스 표시
                x, y, w, h = main_face
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, "Tracking Face", (x, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # 중앙 안내선 표시
            cv2.line(frame, (CAMERA_WIDTH // 2, 0), (CAMERA_WIDTH // 2, CAMERA_HEIGHT), (255, 0, 0), 1)
            cv2.line(frame, (0, CAMERA_HEIGHT // 2), (CAMERA_WIDTH, CAMERA_HEIGHT // 2), (255, 0, 0), 1)
            
            # 현재 각도 표시
            cv2.putText(frame, f"Pan: {gimbal.pan_angle:.1f}, Tilt: {gimbal.tilt_angle:.1f}", 
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            cv2.imshow("Gimbal Face Tracking Test", frame)
            
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
        print("   CareFull Gimbal Hardware Test Tool   ")
        print("========================================")
        print("1. 짐벌 가동 범위 테스트 (단순 회전)")
        print("2. 실시간 얼굴 추적 테스트 (카메라 연동)")
        print("q. 종료")
        
        while True:
            choice = input("\n원하는 테스트 번호를 입력하세요: ")
            
            if choice == '1':
                test_gimbal_movement()
            elif choice == '2':
                test_gimbal_face_tracking()
            elif choice == 'q':
                print("테스트를 종료합니다.")
                break
            else:
                print("잘못된 입력입니다.")
    finally:
        if GPIO:
            logger.info("GPIO 리소스 정리 중...")
            GPIO.cleanup()
