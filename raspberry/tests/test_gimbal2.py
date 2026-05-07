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

class GimbalTest:
    def __init__(self):
        self._picam2 = None
        self._webcam = None
        self.gimbal = None
        
        # 1. 짐벌 초기화 (pigpio 사용)
        try:
            self.gimbal = Gimbal()
            print("[INFO] Gimbal (pigpio) 초기화 완료.")
        except Exception as e:
            print(f"[ERROR] Gimbal 초기화 실패: {e}")

    def _init_camera(self):
        from config.settings import USE_WEBCAM
        print(f"[INFO] 카메라 초기화 시도 중... (USE_WEBCAM: {USE_WEBCAM})")
        
        # 1. Picamera2 시도
        if not USE_WEBCAM:
            try:
                from picamera2 import Picamera2
                self._picam2 = Picamera2()
                config = self._picam2.create_preview_configuration(
                    main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
                )
                self._picam2.configure(config)
                self._picam2.start()
                print("[SUCCESS] Picamera2 가동 성공!")
                return True
            except Exception as e:
                print(f"[WARN] Picamera2 실패: {e}")
                self._picam2 = None

        # 2. USB 웹캠 시도
        for idx in range(3):
            try:
                cap = cv2.VideoCapture(idx)
                if cap.isOpened():
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
        
        return False

    def get_frame(self):
        try:
            if self._picam2:
                frame = self._picam2.capture_array()
                frame = cv2.flip(frame, -1)
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            elif self._webcam:
                ok, frame = self._webcam.read()
                if ok:
                    return cv2.flip(frame, -1)
        except Exception as e:
            print(f"[ERROR] 프레임 획득 실패: {e}")
        return None

    def run_sweep_test(self):
        """기본적인 좌우 회전 테스트"""
        if not self.gimbal: return
        print("\n[INFO] 짐벌 가동 범위 테스트 시작 (0 -> 180 -> 90)")
        test_angles = [90, 45, 0, 45, 90, 135, 180, 135, 90]
        for angle in test_angles:
            print(f"  - 이동 각도: {angle}")
            self.gimbal.set_angle(angle)
            time.sleep(0.5)
        print("[INFO] 가동 범위 테스트 완료.\n")

    def run_tracking_test(self):
        """얼굴 인식 추적 테스트"""
        if not self._init_camera():
            print("[ERROR] 카메라를 초기화할 수 없어 추적 테스트를 건너뜁니다.")
            return

        print("[작동 중] 'q': 종료, 's': 색상 보정 토글")
        cv2.namedWindow("Gimbal Tracking Test (pigpio)", cv2.WINDOW_AUTOSIZE)
        swap_color = False

        try:
            while True:
                frame = self.get_frame()
                if frame is None: continue

                faces = detect_face(frame)
                display_frame = frame.copy()
                if swap_color:
                    display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

                if faces:
                    faces.sort(key=lambda f: f[2] * f[3], reverse=True)
                    target = faces[0]
                    if self.gimbal:
                        self.gimbal.track_face(target, WIDTH, HEIGHT)
                    
                    x, y, w, h = target
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

                cv2.imshow("Gimbal Tracking Test (pigpio)", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'): break
                elif key == ord('s'): swap_color = not swap_color

                if cv2.getWindowProperty("Gimbal Tracking Test (pigpio)", cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            cv2.destroyAllWindows()

    def close(self):
        if self.gimbal: self.gimbal.stop()
        if self._picam2: self._picam2.stop()
        if self._webcam: self._webcam.release()
        print("[INFO] 테스트 종료 및 리소스 해제 완료.")

if __name__ == "__main__":
    tester = GimbalTest()
    try:
        # 1. 먼저 하드웨어 작동 확인 (Sweep)
        tester.run_sweep_test()
        
        # 2. 사용자 선택에 따라 추적 테스트 진행 (CLI 환경 대비)
        if "DISPLAY" in os.environ:
            tester.run_tracking_test()
        else:
            print("[WARN] 디스플레이가 감지되지 않아 얼굴 추적(UI) 테스트는 생략합니다.")
    except KeyboardInterrupt:
        print("\n[STOP] 사용자에 의해 중단되었습니다.")
    finally:
        tester.close()
