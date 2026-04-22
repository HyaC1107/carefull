import json
import os

from config.settings import DB_DIR
from face_recognition.embedding import get_embedding

DB_PATH = os.path.join(DB_DIR, "user_db.json")


def register_user(name, face_img):
    embedding = get_embedding(face_img).tolist()

    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = {}

    db[name] = embedding

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f)

    print(f"{name} registered")
