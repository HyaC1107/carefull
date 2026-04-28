import json
import logging
import os

from config.settings import DB_DIR
from face_recognition.embedding import get_embedding

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(DB_DIR, "user_db.json")


def register_user(name: str, face_img):
    embedding = get_embedding(face_img).tolist()

    # 로컬 저장
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = {}

    db[name] = embedding

    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f)

    # 서버 업로드 (실패해도 로컬은 유지)
    try:
        from api.client import upload_face_embedding
        if not upload_face_embedding(embedding):
            logger.warning("face embedding upload failed for %s", name)
    except Exception as e:
        logger.warning("face embedding upload error: %s", e)

    # 캐시 무효화 → 다음 인증 시 최신 임베딩 사용
    try:
        from auth.authenticate import invalidate_embedding_cache
        invalidate_embedding_cache()
    except Exception:
        pass

    logger.info("%s registered", name)
