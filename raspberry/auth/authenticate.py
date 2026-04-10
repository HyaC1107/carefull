import json
import os

from raspberry.config.settings import DB_DIR
from raspberry.face_recognition.embedding import get_embedding
from raspberry.face_recognition.similarity import cosine_similarity

DB_PATH = os.path.join(DB_DIR, "user_db.json")


def authenticate(face_img, threshold=0.5, expected_user=None):
    try:
        embedding = get_embedding(face_img)
    except Exception:
        return None, -1

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        return None, -1

    best_match = None
    best_score = -1

    for name, saved_emb in db.items():
        if expected_user and name != expected_user:
            continue

        score = cosine_similarity(embedding, saved_emb)
        if score > best_score:
            best_score = score
            best_match = name

    if best_score > threshold:
        return best_match, best_score

    return None, best_score
