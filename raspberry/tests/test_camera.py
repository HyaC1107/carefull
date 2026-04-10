import cv2
from picamera2 import Picamera2

# 카메라 초기화
cam = Picamera2()
# AI 분석에 적합한 작은 사이즈(320x240)로 설정
config = cam.create_preview_configuration(main={"format": 'RGB888', "size": (320, 240)})
cam.configure(config)
cam.start()

print(" OpenCV 미리보기 시작! (종료하려면 'q'를 누르세요)")

try:
    while True:
        # 프레임을 배열 형태로 가져오기
        frame = cam.capture_array()
        
        # Picamera2는 RGB이므로 OpenCV에서 쓰려면 BGR로 변환
        # frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # 화면에 출력
        cv2.imshow('Camera Test', frame)
        
        # 'q' 키를 누르면 루프 탈출
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cam.stop()
    cv2.destroyAllWindows()
    print("✅ 안전하게 종료됨!")