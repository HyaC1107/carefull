import time

import cv2
from picamera2 import Picamera2

from raspberry.config.settings import CAMERA_HEIGHT, CAMERA_WARMUP_SECONDS, CAMERA_WIDTH

picam2 = None


def _init_camera():
    global picam2

    if picam2 is not None:
        return picam2

    camera = Picamera2()
    camera.configure(
        camera.create_preview_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"}
        )
    )
    camera.start()
    time.sleep(CAMERA_WARMUP_SECONDS)
    picam2 = camera
    return picam2


def get_frame():
    try:
        camera = _init_camera()
        frame = camera.capture_array()
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[CAMERA ERROR] {e}")
        return None
