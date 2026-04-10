import time

from raspberry.auth.authenticate import authenticate
from raspberry.camera.camera import get_frame
from raspberry.config.settings import (
    AUTH_RETRY_COUNT,
    AUTH_RETRY_DELAY_SECONDS,
    FACE_MATCH_THRESHOLD,
    SCHEDULE_POLL_SECONDS,
)
from raspberry.face_detection.mediapipe_detector import detect_face
from raspberry.hardware.dispenser import dispense_medicine
from raspberry.scheduler.schedule import check_schedule
from raspberry.utils.logger import save_log


def run_auth_flow(expected_user):
    frame = get_frame()
    if frame is None:
        print("[AUTH] failed to get frame")
        save_log(expected_user, "NO_FRAME")
        return False

    faces = detect_face(frame)
    if not faces:
        print(f"[AUTH] no face detected for {expected_user}")
        save_log(expected_user, "NO_FACE")
        return False

    for (x, y, w, h) in faces:
        face_img = frame[y : y + h, x : x + w]
        name, score = authenticate(
            face_img,
            threshold=FACE_MATCH_THRESHOLD,
            expected_user=expected_user,
        )
        if name:
            print(f"[AUTH SUCCESS] {name} ({score:.2f})")
            dispense_medicine(name)
            save_log(name, "SUCCESS")
            return True

    print(f"[AUTH FAIL] expected={expected_user}")
    save_log(expected_user, "FAIL")
    return False


def main():
    print("[SYSTEM] carefull start (raspberry pi mode)")

    while True:
        due_users = check_schedule()
        if due_users:
            print(f"[SCHEDULE] due users: {due_users}")

            for user in due_users:
                print(f"[AUTH] start for {user}")
                for _ in range(AUTH_RETRY_COUNT):
                    if run_auth_flow(user):
                        break
                    time.sleep(AUTH_RETRY_DELAY_SECONDS)

        time.sleep(SCHEDULE_POLL_SECONDS)


if __name__ == "__main__":
    main()
