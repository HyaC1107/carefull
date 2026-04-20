import cv2
import mediapipe as mp
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from camera.camera import get_frame

_DIST_THRESHOLD = 0.10
_SUCCESS_FRAMES = 5


class BehaviorThread(QThread):
    frame_ready = pyqtSignal(object)         # BGR ndarray (optional display)
    progress_updated = pyqtSignal(int, int)  # current_count, required
    intake_detected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def run(self):
        self._running = True

        mp_hands_mod = mp.solutions.hands
        mp_face_mesh_mod = mp.solutions.face_mesh

        hands = mp_hands_mod.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.1,
            min_tracking_confidence=0.1,
        )
        face_mesh = mp_face_mesh_mod.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        counter = 0

        try:
            while self._running:
                frame = get_frame()
                if frame is None:
                    self.msleep(100)
                    continue

                self.frame_ready.emit(frame.copy())

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb = cv2.flip(rgb, 1)

                hand_res = hands.process(rgb)
                face_res = face_mesh.process(rgb)

                if face_res.multi_face_landmarks and hand_res.multi_hand_landmarks:
                    mouth = face_res.multi_face_landmarks[0].landmark[13]
                    finger = hand_res.multi_hand_landmarks[0].landmark[8]
                    dist = np.hypot(finger.x - mouth.x, finger.y - mouth.y)

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

    def stop(self):
        self._running = False
