import cv2

from config.settings import TEST_IMAGE_PATH, TEST_MODE


def get_frame():
    if TEST_MODE:
        return cv2.imread(TEST_IMAGE_PATH)

    cap = cv2.VideoCapture(0)
    try:
        ok, frame = cap.read()
        if not ok:
            return None
        return frame
    finally:
        cap.release()
