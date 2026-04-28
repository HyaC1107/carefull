"""
파인튜닝 모델 테스트: mobilefacenet_fp32.tflite vs mobilefacenet.tflite
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
_DIR      = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(_DIR, "..", "models")
RASP_DIR  = os.path.join(_DIR, "..", "..", "raspberry")

# ── 모델 로드 (신규 fp32 + 기존 비교용) ───────────────────────────────────────
def load_interpreter(model_filename):
    path = os.path.join(MODEL_DIR, model_filename)
    interp = tflite.Interpreter(model_path=path)
    interp.allocate_tensors()
    return interp, interp.get_input_details(), interp.get_output_details()

interp_fp32, in_fp32, out_fp32 = load_interpreter("mobilefacenet_fp32.tflite")
interp_orig, in_orig, out_orig = load_interpreter("mobilefacenet.tflite")
print("모델 로드 완료 (fp32 + 기존)")

# ── MediaPipe 초기화 ───────────────────────────────────────────────────────────
mp_face       = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.5)

# ── 임베딩 추출 ────────────────────────────────────────────────────────────────
def get_embedding(interp, in_det, out_det, face_bgr):
    if face_bgr.shape[-1] == 4:
        face_bgr = face_bgr[:, :, :3]
    img = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (112, 112))
    img = (img.astype(np.float32) - 127.5) / 128.0
    img = np.expand_dims(img, axis=0)
    interp.set_tensor(in_det[0]["index"], img)
    interp.invoke()
    return interp.get_tensor(out_det[0]["index"])[0]

def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def get_temp():
    raw = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    return float(raw.replace("temp=", "").replace("'C\n", ""))

# ── 로그 저장 ──────────────────────────────────────────────────────────────────
def save_log(score_fp32, score_orig, success, attempts, face_size):
    log = {
        "timestamp":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model":       "mobilefacenet_fp32",
        "score_fp32":  round(score_fp32, 4),
        "score_orig":  round(score_orig, 4),
        "diff":        round(score_fp32 - score_orig, 4),
        "success":     success,
        "attempts":    attempts,
        "face_size":   face_size,
        "cpu_temp":    get_temp(),
        "cpu_usage":   psutil.cpu_percent(),
        "ram_usage":   psutil.virtual_memory().percent,
    }
    log_path = os.path.join(_DIR, "..", "logs", "auth_log_fp32.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logs = []
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            logs = json.load(f)
    logs.append(log)
    with open(log_path, "w") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"[LOG] fp32={score_fp32:.4f}  orig={score_orig:.4f}  diff={log['diff']:+.4f}")

# ── 사용자 임베딩 로드 ─────────────────────────────────────────────────────────
user_path = os.path.join(RASP_DIR, "user_data", "user_002.json")
with open(user_path, "r") as f:
    raw_emb = json.load(f)["embedding"]

# fp32 모델로 저장된 임베딩인지 확인 후 사용
user_embedding = np.array(raw_emb)
print(f"user_002 임베딩 로드 완료 (dim={len(user_embedding)})")

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
print(f"임계값: {THRESHOLD}  |  연속 성공 필요: {SUCCESS_REQUIRED}회")

try:
    while True:
        frame   = picam2.capture_array()
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
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
                emb_fp32  = get_embedding(interp_fp32, in_fp32, out_fp32, face)
                emb_orig  = get_embedding(interp_orig, in_orig, out_orig, face)
                score_fp32 = cosine_similarity(emb_fp32, user_embedding)
                score_orig = cosine_similarity(emb_orig, user_embedding)
                total_attempts += 1

                # fp32 모델 기준으로 인증 판정
                if score_fp32 > THRESHOLD:
                    success_count += 1
                else:
                    success_count = 0

                # 인증 성공
                if success_count >= SUCCESS_REQUIRED:
                    cv2.putText(frame, "AUTH SUCCESS", (50, 50),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                    cv2.imshow("Face Auth - fp32", frame)
                    cv2.waitKey(1500)
                    save_log(score_fp32, score_orig,
                             success=True, attempts=total_attempts, face_size=x2 - x)
                    print("인증 완료")
                    break

                # 화면 표시
                color = (0, 255, 0) if score_fp32 > THRESHOLD else (0, 100, 255)
                cv2.rectangle(frame, (x, y), (x2, y2), color, 2)
                cv2.putText(frame,
                            f"fp32: {score_fp32:.3f}  orig: {score_orig:.3f}  ({success_count}/{SUCCESS_REQUIRED})",
                            (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        else:
            success_count = 0
            cv2.putText(frame, "Waiting for face...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow("Face Auth - fp32", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
