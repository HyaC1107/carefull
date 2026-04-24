"""
얼굴 인증 테스트: MobileFaceNet TFLite + MediaPipe FaceDetection
카메라: Raspberry Pi Camera Module 3 (Picamera2, BGR888)
"""
import cv2
import numpy as np
import mediapipe as mp
import tflite_runtime.interpreter as tflite
import json
import os
import psutil
import subprocess
from datetime import datetime
from picamera2 import Picamera2

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))

# ── MediaPipe 초기화 ───────────────────────────────────────────────────────────
mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# ── MobileFaceNet TFLite 로드 ──────────────────────────────────────────────────
model_path = os.path.join(_DIR, "..", "models", "mobilefacenet.tflite")
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()
input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def get_embedding(face_bgr):
    if face_bgr.shape[-1] == 4:
        face_bgr = face_bgr[:, :, :3]
    face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    face_rgb = cv2.resize(face_rgb, (112, 112))
    face_rgb = (face_rgb.astype(np.float32) - 127.5) / 128
    face_rgb = np.expand_dims(face_rgb, axis=0)
    interpreter.set_tensor(input_details[0]["index"], face_rgb)
    interpreter.invoke()
    return interpreter.get_tensor(output_details[0]["index"])[0]

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_temp():
    raw = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    return float(raw.replace("temp=", "").replace("'C\n", ""))

def save_log(score, success, attempts, face_size):
    log = {
        "timestamp":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id":    "user_002",
        "score":      round(float(score), 4),
        "success":    success,
        "attempts":   attempts,
        "face_size":  face_size,
        "cpu_temp":   get_temp(),
        "cpu_usage":  psutil.cpu_percent(),
        "ram_usage":  psutil.virtual_memory().percent,
    }
    log_path = os.path.join(_DIR, "..", "logs", "auth_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            logs = json.load(f)
    logs.append(log)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

# ── 사용자 임베딩 로드 ─────────────────────────────────────────────────────────
user_path = os.path.join(_DIR, "..", "user_data", "user_002.json")
with open(user_path, "r") as f:
    user_embedding = np.array(json.load(f)["embedding"])
print("user_002 로드 완료")

# ── 판정 파라미터 ──────────────────────────────────────────────────────────────
THRESHOLD        = 0.85
SUCCESS_REQUIRED = 5
success_count    = 0
total_attempts   = 0

# ── 카메라 초기화 ──────────────────────────────────────────────────────────────
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(
    main={"format": "BGR888", "size": (640, 480)}
))
picam2.start()
print("대기 중... 얼굴 감지하면 인증 시작")

try:
    while True:
        frame = picam2.capture_array()          # BGR
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(rgb)

        if results.detections:
            det    = results.detections[0]
            bbox   = det.location_data.relative_bounding_box
            h, w, _ = frame.shape
            margin = 0.2
            x  = max(0, int((bbox.xmin - bbox.width  * margin) * w))
            y  = max(0, int((bbox.ymin - bbox.height * margin) * h))
            x2 = min(w, x + int(bbox.width  * (1 + 2 * margin) * w))
            y2 = min(h, y + int(bbox.height * (1 + 2 * margin) * h))
            face = frame[y:y2, x:x2]

            if face.size != 0:
                emb   = get_embedding(face)
                score = cosine_similarity(emb, user_embedding)
                total_attempts += 1

                if score > THRESHOLD:
                    success_count += 1
                else:
                    success_count = 0

                if success_count >= SUCCESS_REQUIRED:
                    cv2.putText(frame, "AUTH SUCCESS", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                    cv2.imshow("Face Auth", frame)
                    cv2.waitKey(1000)
                    save_log(score=score, success=True,
                             attempts=total_attempts, face_size=x2 - x)
                    print("인증 완료")
                    break

                text = f"{score:.2f} ({success_count}/{SUCCESS_REQUIRED})"
                cv2.rectangle(frame, (x, y), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, text, (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            success_count = 0
            cv2.putText(frame, "Waiting for face...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow("Face Auth", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
