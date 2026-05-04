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
        from config.settings import USE_WEBCAM
        print(f"[INFO] 카메라 초기화 시도 중... (USE_WEBCAM: {USE_WEBCAM})")
        
        # 1. Picamera2 시도 (USE_WEBCAM이 아닐 때만 우선 시도)
        if not USE_WEBCAM:
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
                print(f"[WARN] Picamera2 실패 (USB 웹캠으로 전환 시도): {e}")
                self._picam2 = None

        # 2. 일반 OpenCV 웹캠 시도 (인덱스 0~2까지 순차 시도)
        print("[INFO] USB 웹캠 검색 중 (Index 0~2)...")
        for idx in range(3):
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    # 테스트 프레임 읽기 확인
                    ok, frame = cap.read()
                    if ok:
                        self._webcam = cap
                        self._webcam.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)
                        self._webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
                        print(f"[SUCCESS] USB 웹캠 Index {idx} 가동 성공!")
                        return True
                    cap.release()
            except Exception as e:
                print(f"[DEBUG] Index {idx} 시도 중 에러: {e}")
        
        print("[ERROR] 연결된 USB 웹캠을 찾을 수 없거나 이미 사용 중입니다.")
        print("[TIP] 'ps aux | grep python'으로 다른 카메라 사용 프로세스가 있는지 확인하세요.")
        return False

    def get_frame(self):
        try:
            if self._picam2:
                # Picamera2는 기본적으로 RGB를 반환할 수 있음
                frame = self._picam2.capture_array()
                # 화면 출력이 파랗게 나온다면 여기서 BGR로의 변환이 필요하거나, 
                # 혹은 이미 BGR인데 또 변환해서 생기는 문제일 수 있음.
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

        # 화면 색상이 이상할 경우 (파란색 등) 실행 중 's' 키를 눌러 토글하거나 
        # 아래 기본값을 True/False로 조절하세요.
        self.swap_color = True 

        print(f"\n[INFO] 카메라 소스: {'Picamera2' if self._picam2 else 'USB 웹캠'}")
        print(f"[INFO] 초기 색상 보정(SWAP): {'ON' if self.swap_color else 'OFF'}")
        print("[작동 중] 's': 색상 보정 토글, 'q': 종료")
        
        cv2.namedWindow("CareFull Gimbal Tracking Test", cv2.WINDOW_AUTOSIZE)
        
        try:
            while True:
                frame_bgr = self.get_frame()
                if frame_bgr is None:
                    continue
                
                # 1. 얼굴 인식 수행 (항상 BGR 원본 사용)
                # mediapipe_detector.detect_face는 내부에서 BGR -> RGB 변환을 수행함
                faces = detect_face(frame_bgr)
                
                # 2. 화면 출력용 프레임 준비 (원본 복사)
                display_frame = frame_bgr.copy()
                
                # 색상 채널 교정 (R <-> B) - 화면 표시용으로만 적용
                if self.swap_color:
                    display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                
                # 중앙 조준선 (시각화 - display_frame에 그림)
                cv2.line(display_frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (255, 0, 0), 1)
                
                # 추적할 대상 선정 (가장 큰 얼굴)
                target_face = None
                error_x = 0
                if faces:
                    # 면적이 가장 큰 얼굴 선택
                    faces.sort(key=lambda f: f[2] * f[3], reverse=True)
                    target_face = faces[0]
                    
                    # 짐벌 추적 (hardware/gimbal.py 활용)
                    if self.gimbal:
                        self.gimbal.track_face(target_face, WIDTH, HEIGHT)
                    
                    # 오차값 계산 (화면 표시용)
                    fx = target_face[0] + target_face[2] // 2
                    error_x = fx - (WIDTH // 2)
                
                # 시각화 (display_frame에 그림)
                for i, (x, y, w, h) in enumerate(faces):
                    color = (0, 255, 0) if i == 0 else (255, 255, 0)
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                    cv2.circle(display_frame, (x + w // 2, y + h // 2), 5, (0, 0, 255), -1)

                # 상태 정보 표시
                if self.gimbal:
                    cv2.putText(display_frame, f"Angle: {self.gimbal.angle:.1f}", (20, 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(display_frame, f"Error X: {error_x}", (20, 70), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(display_frame, f"SWAP: {'ON' if self.swap_color else 'OFF'}", (20, 100), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
                
                cv2.imshow("CareFull Gimbal Tracking Test", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'): # 's' 키를 누르면 실시간으로 색상 반전 토글
                    self.swap_color = not self.swap_color
                    print(f"[INFO] 색상 보정 토글: {'ON' if self.swap_color else 'OFF'}")
                
                if cv2.getWindowProperty("CareFull Gimbal Tracking Test", cv2.WND_PROP_VISIBLE) < 1:
                    break
                
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
