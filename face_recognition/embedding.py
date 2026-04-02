import os

import cv2
import numpy as np

from config.settings import MODELS_DIR, TEST_MODE

if not TEST_MODE:
    from face_recognition.model_loader import FaceModel

    model = FaceModel(os.path.join(MODELS_DIR, "mobilefacenet.tflite"))
else:
    model = None


def get_embedding(face_img):
    if face_img is None or face_img.size == 0:
        raise ValueError("face image is empty")

    if TEST_MODE:
        # Keep test-mode embeddings deterministic across runs on the same image.
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (16, 8)).astype(np.float32).flatten()
        normalized = resized / 255.0
        norm = np.linalg.norm(normalized)
        return normalized if norm == 0 else normalized / norm

    return model.predict(face_img)
