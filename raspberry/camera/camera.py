import os
import time

import cv2

from config.settings import CAMERA_HEIGHT, CAMERA_WARMUP_SECONDS, CAMERA_WIDTH

# CAREFULL_USE_WEBCAM=1 이면 PC 웹캠, 아니면 Picamera2 시도 후 폴백
_USE_WEBCAM = os.getenv("CAREFULL_USE_WEBCAM", "0") == "1"

_picam2 = None
_webcam: cv2.VideoCapture | None = None


# ──────────────────────────────── Picamera2 ───────────────────────────────────

def _init_picamera():
    global _picam2
    if _picam2 is not None:
        return _picam2
    from picamera2 import Picamera2
    cam = Picamera2()
    cam.configure(
        cam.create_preview_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"}
        )
    )
    cam.start()
    time.sleep(CAMERA_WARMUP_SECONDS)
    _picam2 = cam
    return _picam2


def _get_frame_picamera() -> "cv2.ndarray | None":
    try:
        cam = _init_picamera()
        frame = cam.capture_array()
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[CAMERA/PICAM ERROR] {e}")
        return None


# ──────────────────────────────── cv2 webcam ─────────────────────────────────

def _init_webcam():
    global _webcam
    if _webcam is not None and _webcam.isOpened():
        return _webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    time.sleep(CAMERA_WARMUP_SECONDS)
    _webcam = cap
    return _webcam


def _get_frame_webcam() -> "cv2.ndarray | None":
    try:
        cap = _init_webcam()
        ok, frame = cap.read()
        return frame if ok else None
    except Exception as e:
        print(f"[CAMERA/WEBCAM ERROR] {e}")
        return None


# ──────────────────────────────── 공개 API ───────────────────────────────────

def get_frame():
    """RPi: Picamera2 / PC: cv2.VideoCapture(0) 자동 전환."""
    if _USE_WEBCAM:
        return _get_frame_webcam()

    # Picamera2 시도, 실패하면 웹캠으로 폴백
    try:
        return _get_frame_picamera()
    except Exception:
        return _get_frame_webcam()
