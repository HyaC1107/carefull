import sys
import os
import time
import cv2
import numpy as np

# MediaPipe 예외 처리
try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

WIDTH = 640
HEIGHT = 480

class RobustCameraTester:
    def __init__(self):
        self._picam2 = None
        self._webcam = None
        self._face_detection = None
        
        # 디스플레이 환경 확인
        if "DISPLAY" not in os.environ:
            print("[ERROR] 디스플레이 환경 변수가 없습니다. SSH 접속 중이라면 'ssh -X' 또는 VNC를 사용하세요.")

        if HAS_MEDIAPIPE:
            try:
                mp_face = mp.solutions.face_detection
                self._face_detection = mp_face.FaceDetection(
                    model_selection=0, min_detection_confidence=0.5
                )
                print("[INFO] MediaPipe Face Detection 초기화 완료.")
            except Exception as e:
                print(f"[ERROR] MediaPipe 초기화 실패: {e}")

    def _init_camera(self):
        print("[INFO] 카메라 초기화 시도 중...")
        
        # 1. Picamera2 시도 (rpicam-hello와 같은 스택)
        try:
            from picamera2 import Picamera2
            print("[INFO] Picamera2 라이브러리 로드 성공. 카메라 객체 생성 중...")
            self._picam2 = Picamera2()
            
            # 카메라 설정 (rpicam-hello와 유사한 설정)
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
                # Picamera2 프레임 캡처
                frame = self._picam2.capture_array()
                # 180도 회전 (상하 반전 대응)
                frame = cv2.flip(frame, -1)
                return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            elif self._webcam:
                ok, frame = self._webcam.read()
                if ok:
                    # 180도 회전
                    return cv2.flip(frame, -1)
                return None
        except Exception as e:
            print(f"[ERROR] 프레임 획득 실패: {e}")
        return None

    def detect_face(self, frame):
        if not self._face_detection or frame is None:
            return []
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._face_detection.process(rgb_frame)
            faces = []
            if results.detections:
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    x, y, w, h = int(bbox.xmin*WIDTH), int(bbox.ymin*HEIGHT), int(bbox.width*WIDTH), int(bbox.height*HEIGHT)
                    faces.append((x, y, w, h))
            return faces
        except Exception:
            return []

    def run(self):
        if not self._init_camera():
            print("[FATAL] 모든 카메라 초기화 수단이 실패했습니다.")
            return

        print("\n[작동 중] 화면이 뜨는지 확인하세요. 'q'를 누르면 종료됩니다.")
        print("[TIP] 색상이 이상하면 's' 키를 눌러보세요.")
        
        cv2.namedWindow("CareFull Camera Test", cv2.WINDOW_AUTOSIZE)
        swap_color = False
        
        try:
            while True:
                frame = self.get_frame()
                if frame is None:
                    continue
                
                if swap_color:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                faces = self.detect_face(frame)
                
                # 시각화 (중앙 조준선)
                cv2.line(frame, (WIDTH//2, 0), (WIDTH//2, HEIGHT), (255, 0, 0), 1)
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.circle(frame, (x + w // 2, y + h // 2), 5, (0, 0, 255), -1)

                cv2.imshow("CareFull Camera Test", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    swap_color = not swap_color
                
                if cv2.getWindowProperty("CareFull Camera Test", cv2.WND_PROP_VISIBLE) < 1:
                    break
        except KeyboardInterrupt:
            print("\n[STOP] 사용자에 의해 중단되었습니다.")
        finally:
            if self._picam2: self._picam2.stop()
            if self._webcam: self._webcam.release()
            cv2.destroyAllWindows()
            print("[INFO] 리소스가 해제되었습니다.")

if __name__ == "__main__":
    tester = RobustCameraTester()
    tester.run()
