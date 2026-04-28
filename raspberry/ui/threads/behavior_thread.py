from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE, MODELS_DIR
import os

_DIST_THRESHOLD = 0.13
_SUCCESS_FRAMES = 5
_YOLO_MODEL_PATH = os.path.join(MODELS_DIR, "yolo26n-pose_ncnn_model")
_YOLO_IMGSZ = 640
_YOLO_CONF = 0.3

_KP_NOSE    = 0
_KP_L_WRIST = 9
_KP_R_WRIST = 10
_KP_MOUTH   = 13  # FaceMesh landmark


class BehaviorThread(QThread):
    frame_ready = pyqtSignal(object)         # BGR ndarray (optional display)
    progress_updated = pyqtSignal(int, int)  # current_count, required
    intake_detected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def run(self):
        self._running = True
        if UI_TEST_MODE:
            for i in range(1, _SUCCESS_FRAMES + 1):
                if not self._running:
                    return
                self.progress_updated.emit(i, _SUCCESS_FRAMES)
                self.msleep(400)
            if self._running:
                self.intake_detected.emit()
            return

        import cv2
        import mediapipe as mp
        import numpy as np
        from ultralytics import YOLO
        from camera.camera import get_frame

        yolo = YOLO(_YOLO_MODEL_PATH)

        mp_face_mesh_mod = mp.solutions.face_mesh
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
                h, w = rgb.shape[:2]

                # FaceMesh로 입 좌표 추출
                face_res = face_mesh.process(rgb)
                mouth = None
                if face_res.multi_face_landmarks:
                    lm = face_res.multi_face_landmarks[0].landmark[_KP_MOUTH]
                    mouth = (lm.x, lm.y)

                # YOLO Pose로 손목 좌표 추출
                wrist = None
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                results = yolo(bgr, imgsz=_YOLO_IMGSZ, verbose=False)
                for r in results:
                    if r.keypoints is None or len(r.keypoints.data) == 0:
                        break
                    kps = r.keypoints.data[0]  # (17, 3): x_px, y_px, conf
                    l_kp = kps[_KP_L_WRIST]
                    r_kp = kps[_KP_R_WRIST]

                    dist_l = dist_r = float("inf")
                    if l_kp[2] >= _YOLO_CONF:
                        dist_l = float(np.hypot(l_kp[0] / w - mouth[0], l_kp[1] / h - mouth[1])) if mouth else float("inf")
                    if r_kp[2] >= _YOLO_CONF:
                        dist_r = float(np.hypot(r_kp[0] / w - mouth[0], r_kp[1] / h - mouth[1])) if mouth else float("inf")

                    closer = l_kp if dist_l <= dist_r else r_kp
                    if closer[2] >= _YOLO_CONF:
                        wrist = (closer[0].item() / w, closer[1].item() / h)
                    break

                if mouth and wrist:
                    dist = np.hypot(wrist[0] - mouth[0], wrist[1] - mouth[1])
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
            face_mesh.close()

    def stop(self):
        self._running = False
