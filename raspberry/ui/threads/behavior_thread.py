from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE

_DIST_THRESHOLD = 0.20   # 정규화 거리 (코 ↔ 손목)
_SUCCESS_FRAMES = 5      # 연속 감지 프레임 수

_NOSE    = 0
_L_WRIST = 15
_R_WRIST = 16


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

        pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        counter = 0

        try:
            while self._running:
                frame = get_frame()   # BGR
                if frame is None:
                    self.msleep(50)
                    continue

                self.frame_ready.emit(frame.copy())

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = rgb.shape[:2]

                results = pose.process(rgb)

                is_near = False
                if results.pose_landmarks:
                    lm      = results.pose_landmarks.landmark
                    nose    = lm[_NOSE]
                    l_wrist = lm[_L_WRIST]
                    r_wrist = lm[_R_WRIST]

                    dist_l = float(np.hypot(l_wrist.x - nose.x, l_wrist.y - nose.y))
                    dist_r = float(np.hypot(r_wrist.x - nose.x, r_wrist.y - nose.y))

                    if min(dist_l, dist_r) < _DIST_THRESHOLD:
                        is_near = True

                if is_near:
                    counter += 1
                else:
                    counter = max(0, counter - 1)

                self.progress_updated.emit(counter, _SUCCESS_FRAMES)

                if counter >= _SUCCESS_FRAMES:
                    if self._running:
                        self.intake_detected.emit()
                    return

        finally:
            pose.close()

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
