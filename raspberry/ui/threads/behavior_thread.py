import csv
import datetime
import os

from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE, BASE_DIR

_DIST_THRESHOLD = 0.3   # 정규화 거리 (코 ↔ 손목)
_SUCCESS_FRAMES = 4      # 연속 감지 프레임 수

_LOG_PATH = os.path.join(BASE_DIR, "logs", "behavior_log.csv")

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

        import cv2
        import mediapipe as mp
        import numpy as np
        from camera.camera import get_frame
        from hardware.gimbal import Gimbal

        pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        gimbal = Gimbal()

        counter = 0
        frame_no = 0
        session_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session_logs = []

        try:
            while self._running:
                frame = get_frame()   # BGR
                if frame is None:
                    self.msleep(50)
                    continue

                self.frame_ready.emit(frame.copy())

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                fh, fw = rgb.shape[:2]

                results = pose.process(rgb)

                is_near = False
                dist_l = dist_r = -1.0
                if results.pose_landmarks:
                    lm      = results.pose_landmarks.landmark
                    nose    = lm[_NOSE]
                    l_wrist = lm[_L_WRIST]
                    r_wrist = lm[_R_WRIST]

                    nose_cx = int(nose.x * fw)
                    nose_cy = int(nose.y * fh)
                    face_sz = int(fh * 0.25)
                    gimbal.track_face(
                        (nose_cx - face_sz // 2, nose_cy - face_sz // 2, face_sz, face_sz),
                        fw, fh
                    )

                    dist_l = float(np.hypot(l_wrist.x - nose.x, l_wrist.y - nose.y))
                    dist_r = float(np.hypot(r_wrist.x - nose.x, r_wrist.y - nose.y))

                    if min(dist_l, dist_r) < _DIST_THRESHOLD:
                        is_near = True
                else:
                    gimbal.update_idle()

                if is_near:
                    counter += 1
                else:
                    counter = max(0, counter - 1)

                frame_no += 1
                session_logs.append((
                    session_ts, frame_no,
                    round(dist_l, 4), round(dist_r, 4),
                    round(min(dist_l, dist_r), 4) if dist_l >= 0 else -1.0,
                    1 if is_near else 0,
                    counter,
                ))

                self.progress_updated.emit(counter, _SUCCESS_FRAMES)

                if counter >= _SUCCESS_FRAMES:
                    if self._running:
                        _save_behavior_log(session_logs, detected=True)
                        self.intake_detected.emit()
                    return

        finally:
            pose.close()
            gimbal.stop()
            if session_logs and counter < _SUCCESS_FRAMES:
                _save_behavior_log(session_logs, detected=False)

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


def _save_behavior_log(session_logs: list, detected: bool):
    """복약행위 감지 결과를 CSV에 추가."""
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(_LOG_PATH)
    try:
        with open(_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow([
                    "session_time", "frame_no",
                    "dist_left_wrist", "dist_right_wrist", "min_dist",
                    "is_near", "counter", "final_detected",
                ])
            final = 1 if detected else 0
            for row in session_logs:
                w.writerow(list(row) + [final])
    except Exception as e:
        print(f"[BEHAVIOR_LOG] 로그 저장 실패: {e}")
