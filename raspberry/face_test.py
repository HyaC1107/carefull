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

# ----------------------
# MediaPipe
# ----------------------
mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# ----------------------
# 모델
# ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "models", "mobilefacenet.tflite")

interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def get_embedding(face_img):
    if face_img.shape[-1] == 4:
        face_img = face_img[:, :, :3]
    face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    face_img = cv2.resize(face_img, (112, 112))
    face_img = (face_img.astype(np.float32) - 127.5) / 128
    face_img = np.expand_dims(face_img, axis=0)

    interpreter.set_tensor(input_details[0]['index'], face_img)
    interpreter.invoke()

    return interpreter.get_tensor(output_details[0]['index'])[0]

# ----------------------
# cosine similarity
# ----------------------
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_temp():
    raw = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    return float(raw.replace("temp=", "").replace("'C\n", ""))

def save_log(score, success, attempts, face_size):
    log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": "user_001",
        "score": round(float(score), 4),
        "success": success,
        "attempts": attempts,
        "face_size": face_size,
        "cpu_temp": get_temp(),
        "cpu_usage": psutil.cpu_percent(),
        "ram_usage": psutil.virtual_memory().percent
    }

    log_path = os.path.join(BASE_DIR, "logs", "auth_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(log)

    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
# ----------------------
# user_001 로드
# ----------------------
user_path = os.path.join(BASE_DIR, "user_data", "user_002.json")

with open(user_path, "r") as f:
    data = json.load(f)
    user_embedding = np.array(data["embedding"])

print("user_001 로드 완료")

# ----------------------
# 카운터 설정
# ----------------------
THRESHOLD = 0.85
SUCCESS_REQUIRED = 5

success_count = 0
total_attempts = 0
# ----------------------
# 카메라
# ----------------------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

print("👉 대기 중... 얼굴 감지하면 인증 시작")

while True:
    frame = picam2.capture_array()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb)

    if results.detections:
        det = results.detections[0]

        bbox = det.location_data.relative_bounding_box

        h, w, _ = frame.shape
        margin = 0.2
        x = max(0, int((bbox.xmin - bbox.width * margin) * w))
        y = max(0, int((bbox.ymin - bbox.height * margin) * h))
        bw = int(bbox.width * (1 + 2 * margin) * w)
        bh = int(bbox.height * (1 + 2 * margin) * h)

        x = max(0, x)
        y = max(0, y)
        x2 = min(w, x + bw)
        y2 = min(h, y + bh)

        face = frame[y:y2, x:x2]

        if face.size != 0:
            emb = get_embedding(face)
            score = cosine_similarity(emb, user_embedding)
            total_attempts += 1  # ← 추가
            # ----------------------
            # 연속 성공 로직
            # ----------------------
            if score > THRESHOLD:
                success_count += 1
            else:
                success_count = 0  # 실패하면 초기화

            # ----------------------
            # 인증 판단
            # ----------------------
            if success_count >= SUCCESS_REQUIRED:
                cv2.putText(rgb, "AUTH SUCCESS", (50,50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 3)
                cv2.imshow("Face Auth", rgb)
                cv2.waitKey(1000)
                save_log(
                    score=score,
                    success=True,
                    attempts=total_attempts,
                    face_size=bw
                )
                print("✅ 인증 완료")
                break
            print("score:", score)
            text = f"{score:.2f} ({success_count}/{SUCCESS_REQUIRED})"

            cv2.rectangle(rgb, (x, y), (x2, y2), (0,255,0), 2)
            cv2.putText(rgb, text, (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,0), 2)

    else:
        success_count = 0
        cv2.putText(rgb, "Waiting for face...", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)

    cv2.imshow("Face Auth", rgb)

    if cv2.waitKey(1) & 0xFF == 27:
        break

picam2.stop()
cv2.destroyAllWindows()