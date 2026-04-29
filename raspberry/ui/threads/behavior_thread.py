from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE

_DIST_THRESHOLD = 0.13   # 정규화 거리 (손가락 끝 ↔ 입)
_SUCCESS_FRAMES = 5      # 연속 감지 프레임 수
_FINGER_TIPS    = [4, 8, 12, 16, 20]   # 엄지·검지·중지·약지·소지 끝
_MOUTH_LM       = 13     # FaceMesh 상순 중앙


class BehaviorThread(QThread):
    frame_ready      = pyqtSignal(object)   # BGR ndarray (화면 표시용)
    progress_updated = pyqtSignal(int, int) # current, required
    intake_detected  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def run(self):
        self._running = True

        if UI_TEST_MODE:
            self._run_test_mode()
            return

        import cv2
        import mediapipe as mp
        import numpy as np
        from camera.camera import get_frame

        hands = mp.solutions.hands.Hands(
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        counter = 0

        try:
            while self._running:
                frame = get_frame()
                if frame is None:
                    self.msleep(50)
                    continue

                self.frame_ready.emit(frame.copy())

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]

                # 입 좌표 (FaceMesh)
                mouth = None
                face_res = face_mesh.process(rgb)
                if face_res.multi_face_landmarks:
                    lm = face_res.multi_face_landmarks[0].landmark[_MOUTH_LM]
                    mouth = (lm.x, lm.y)

                # 손가락 끝 좌표 (MediaPipe Hands)
                finger_tip = None
                if mouth:
                    hand_res = hands.process(rgb)
                    if hand_res.multi_hand_landmarks:
                        best_dist = float('inf')
                        for hand_lm in hand_res.multi_hand_landmarks:
                            for tip_idx in _FINGER_TIPS:
                                tip = hand_lm.landmark[tip_idx]
                                d = float(np.hypot(tip.x - mouth[0],
                                                   tip.y - mouth[1]))
                                if d < best_dist:
                                    best_dist = d
                                    finger_tip = (tip.x, tip.y)

                # 거리 판정
                if mouth and finger_tip:
                    dist = float(np.hypot(finger_tip[0] - mouth[0],
                                         finger_tip[1] - mouth[1]))
                    if dist < _DIST_THRESHOLD:
                        counter += 1
                    else:
                        counter = max(0, counter - 1)
                else:
                    counter = max(0, counter - 1)

                self.progress_updated.emit(counter, _SUCCESS_FRAMES)

                if counter >= _SUCCESS_FRAMES:
                    if self._running:
                        self.intake_detected.emit()
                    return

        finally:
            hands.close()
            face_mesh.close()

    def _run_test_mode(self):
        for i in range(1, _SUCCESS_FRAMES + 1):
            if not self._running:
                return
            self.progress_updated.emit(i, _SUCCESS_FRAMES)
            self.msleep(400)
        if self._running:
            self.intake_detected.emit()

    def stop(self):
        self._running = False
