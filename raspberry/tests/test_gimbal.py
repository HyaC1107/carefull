import sys
import os
import time
import cv2
import numpy as np

# 프로젝트 루트 경로 추가 (모듈 임포트를 위해)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# 프로젝트 모듈 임포트
from face_detection.mediapipe_detector import detect_face
from hardware.gimbal import Gimbal
from config.settings import CAMERA_WIDTH as WIDTH, CAMERA_HEIGHT as HEIGHT

# GPIO 및 카메라 라이브러리 예외 처리 (설치 여부 확인)
try:
    import RPi.GPIO as GPIO
except ImportError:
    print("[WARN] RPi.GPIO를 찾을 수 없습니다. 시뮬레이션 모드로 작동합니다.")

class GimbalFaceTracker:
    def __init__(self):
        self._picam2 = None
        self._webcam = None
        
        # 1. 짐벌 초기화
        try:
            GPIO.setmode(GPIO.BCM)
            self.gimbal = Gimbal()
            print("[INFO] Gimbal (Pin 19) 초기화 완료.")
        except Exception as e:
            print(f"[ERROR] Gimbal 초기화 실패: {e}")
            self.gimbal = None

        # 디스플레이 환경 확인
        if "DISPLAY" not in os.environ:
            print("[WARN] 디스플레이 환경 변수가 없습니다. 창이 뜨지 않을 수 있습니다.")

    def _init_camera(self):
        print("[INFO] 카메라 초기화 시도 중...")
        
        # 1. Picamera2 시도
        try:
            from picamera2 import Picamera2
            print("[INFO] Picamera2 라이브러리 로드 성공. 카메라 객체 생성 중...")
            self._picam2 = Picamera2()
            
            config = self._picam2.create_preview_configuration(
                main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
            )
            self._picam2.configure(config)
            self._picam2.start()
            
            print("[SUCCESS] Picamera2 가동 성공!")
            return True
        except Exception as e:
            print(f"[WARN] Picamera2 실패 사유: {e}")
            self._picam2 = None

        # 2. 일반 OpenCV 웹캠 시도 (폴백)
        print("[INFO] USB 웹캠 모드로 전환하여 시도 중...")
        try:
            self._webcam = cv2.VideoCapture(0)
            if self._webcam.isOpened():
                self._webcam.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
                self._webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
                print("[SUCCESS] USB 웹캠 가동 성공!")
                return True
            else:
                print("[ERROR] 연결된 USB 웹캠을 찾을 수 없습니다.")
        except Exception as e:
            print(f"[ERROR] 웹캠 초기화 실패: {e}")
        
        return False

    def get_frame(self):
        try:
            if self._picam2:
                frame = self._picam2.capture_array()
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            elif self._webcam:
                ok, frame = self._webcam.read()
                return frame if ok else None
        except Exception as e:
            print(f"[ERROR] 프레임 획득 실패: {e}")
        return None

    def run(self):
        if not self._init_camera():
            print("[FATAL] 모든 카메라 초기화 수단이 실패했습니다.")
            return

        print("\n[작동 중] 얼굴 추적 테스트를 시작합니다. 'q'를 누르면 종료됩니다.")
        
        cv2.namedWindow("CareFull Gimbal Tracking Test", cv2.WINDOW_AUTOSIZE)
        
        try:
            while True:
                frame = self.get_frame()
                if frame is None:
                    print("[WARN] 프레임이 비어있습니다. 재시도 중...")
                    time.sleep(0.1)
                    continue
                
                # 얼굴 인식 (mediapipe_detector 활용)
                faces = detect_face(frame)
                
                # 중앙 조준선 (시각화)
                cv2.line(frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (255, 0, 0), 1)
                
                # 추적할 대상 선정 (가장 큰 얼굴)
                target_face = None
                if faces:
                    # 면적이 가장 큰 얼굴 선택
                    faces.sort(key=lambda f: f[2] * f[3], reverse=True)
                    target_face = faces[0]
                    
                    # 짐벌 추적 (hardware/gimbal.py 활용)
                    if self.gimbal:
                        self.gimbal.track_face(target_face, WIDTH, HEIGHT)
                
                # 시각화
                for i, (x, y, w, h) in enumerate(faces):
                    color = (0, 255, 0) if i == 0 else (255, 255, 0) # 타겟은 녹색, 나머지는 하늘색계열
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    cv2.circle(frame, (x + w // 2, y + h // 2), 5, (0, 0, 255), -1)

                # 상태 정보 표시
                if self.gimbal:
                    cv2.putText(frame, f"Gimbal Angle: {self.gimbal.angle:.1f}", (20, 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                cv2.imshow("CareFull Gimbal Tracking Test", frame)
                
                # 'q' 키를 누르거나 창을 닫으면 종료
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                if cv2.getWindowProperty("CareFull Gimbal Tracking Test", cv2.WND_PROP_VISIBLE) < 1:
                    break
        except KeyboardInterrupt:
            print("\n[STOP] 사용자에 의해 중단되었습니다.")
        finally:
            if self.gimbal:
                self.gimbal.stop()
            if self._picam2: self._picam2.stop()
            if self._webcam: self._webcam.release()
            GPIO.cleanup()
            cv2.destroyAllWindows()
            print("[INFO] 리소스가 해제되었습니다.")

if __name__ == "__main__":
    tracker = GimbalFaceTracker()
    tracker.run()
