import cv2
from behavior.intake_detector import IntakeDetector

def main():
    cap = cv2.VideoCapture(0) # 라파 카메라 모듈
    detector = IntakeDetector()
    
    print("💊 복약 행위 검증 테스트 시작 (Q를 누르면 종료)")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1) # 거울 모드
        intake_success, dist = detector.detect_intake(frame)
        
        # 화면 표시
        color = (0, 255, 0) if intake_success else (0, 0, 255)
        status_text = "INTAKE SUCCESS!" if intake_success else "Waiting..."
        
        cv2.putText(frame, f"Dist: {dist:.4f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv2.putText(frame, status_text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        cv2.imshow('CareFull Behavior Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    detector.release()

if __name__ == "__main__":
    main()