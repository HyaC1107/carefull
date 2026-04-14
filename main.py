import cv2
import numpy as np
import mediapipe as mp
import tflite_runtime.interpreter as tflite
import json
import os
import time
from picamera2 import Picamera2

# ----------------------
# MediaPipe
# ----------------------
mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# ----------------------
# 모델 경로
# ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "models", "mobilefacenet.tflite")

# ----------------------
# MobileFaceNet
# ----------------------
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
# picamera2 시작
# ----------------------
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

embeddings = []
capture_count = 0
TARGET_COUNT = 20
capture_mode = False

print("👉 S 누르면 얼굴 등록 시작")

while True:
    frame = picam2.capture_array()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_detection.process(rgb)

    key = cv2.waitKey(1) & 0xFF

    # 촬영 시작
    if key == ord('s'):
        print("📸 촬영 시작!")
        capture_mode = True
        capture_count = 0
        embeddings = []

    if results.detections and capture_mode:
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
            embeddings.append(emb)
            capture_count += 1

            print(f"캡처 {capture_count}/{TARGET_COUNT}")

            cv2.rectangle(rgb, (x, y), (x2, y2), (0,255,0), 2)

            time.sleep(0.5)

        if capture_count >= TARGET_COUNT:
            capture_mode = False
            print("✅ 촬영 완료!")

    # UI
    if not capture_mode:
        cv2.putText(rgb, "Press S to Register", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    else:
        cv2.putText(rgb, f"Capturing... {capture_count}/5", (10,30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)

    cv2.imshow("Face Register", rgb)

    if key == 27:
        break

    if capture_count >= TARGET_COUNT:
        break

picam2.stop()
cv2.destroyAllWindows()

# ----------------------
# 저장
# ----------------------
if len(embeddings) == 0:
    print("❌ 얼굴 인식 실패")
    exit()

mean_embedding = np.mean(np.array(embeddings), axis=0)

os.makedirs(os.path.join(BASE_DIR, "user_data"), exist_ok=True)

user_id = "user_002"
file_path = os.path.join(BASE_DIR, "user_data", f"{user_id}.json")

user_data = {
    "user_id": user_id,
    "embedding": mean_embedding.tolist()
}

with open(file_path, "w") as f:
    json.dump(user_data, f)

print(f"🎉 등록 완료! → {file_path}")