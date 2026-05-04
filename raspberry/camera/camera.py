import os
import time

import cv2

from config.settings import CAMERA_HEIGHT, CAMERA_WARMUP_SECONDS, CAMERA_WIDTH

# CAREFULL_USE_WEBCAM=1 이면 PC 웹캠, 아니면 Picamera2 시도 후 폴백
_USE_WEBCAM = os.getenv("CAREFULL_USE_WEBCAM", "0") == "1"

_picam2 = None
_webcam: cv2.VideoCapture | None = None
_picam2_available = True # Picamera2 가동 가능 여부 플래그


# ──────────────────────────────── Picamera2 ───────────────────────────────────

def _init_picamera():
    global _picam2, _picam2_available
    if _picam2 is not None:
        return _picam2
    if not _picam2_available:
        return None
        
    try:
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
    except Exception as e:
        _picam2_available = False # 한 번 실패하면 해당 세션에서는 다시 시도하지 않음
        print(f"[CAMERA/PICAM ERROR] {e} - Picamera2 disabled, falling back to webcam.")
        return None


def _get_frame_picamera() -> "cv2.ndarray | None":
    cam = _init_picamera()
    if cam is None:
        return None
    try:
        frame = cam.capture_array()
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"[CAMERA/PICAM CAPTURE ERROR] {e}")
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

def release_camera():
    """사용 중인 카메라 리소스 해제"""
    global _picam2, _webcam
    if _picam2 is not None:
        try:
            _picam2.stop()
        except Exception:
            pass
        try:
            # close()까지 호출해야 HAL 리소스가 "Available" 상태로 돌아옴
            # stop()만 하면 "Configured" 상태로 남아 다음 Picamera2() 초기화 실패
            _picam2.close()
        except Exception:
            pass
        _picam2 = None
        print("[CAMERA] Picamera2 stopped.")

    if _webcam is not None:
        try:
            _webcam.release()
        except Exception:
            pass
        _webcam = None
        print("[CAMERA] Webcam released.")

def check_camera_health():
    """카메라가 정상적으로 프레임을 가져오는지 확인"""
    try:
        frame = get_frame()
        if frame is not None and frame.size > 0:
            return True
        return False
    except Exception:
        return False

def get_frame():
    """RPi: Picamera2 / PC: cv2.VideoCapture(0) 자동 전환."""
    if _USE_WEBCAM:
        return _get_frame_webcam()

    # Picamera2 시도, 실패하면 웹캠으로 폴백
    try:
        return _get_frame_picamera()
    except Exception:
        return _get_frame_webcam()
