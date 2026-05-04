import json
import logging
import os

from config.settings import DB_DIR, FACE_MATCH_THRESHOLD
from face_recognition.embedding import get_embedding
from face_recognition.similarity import cosine_similarity

logger = logging.getLogger(__name__)
DB_PATH = os.path.join(DB_DIR, "user_db.json")

# 서버 임베딩 메모리 캐시 (TTL: 5분)
_EMBEDDING_CACHE_TTL = 300
_embedding_cache: dict = {}
_embedding_cache_ts: float = 0.0


def _load_local() -> dict:
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _load_server() -> dict:
    import time
    global _embedding_cache, _embedding_cache_ts

    if _embedding_cache and (time.monotonic() - _embedding_cache_ts) < _EMBEDDING_CACHE_TTL:
        return _embedding_cache

    try:
        from api.client import fetch_face_embeddings
        records = fetch_face_embeddings()
        result = {}
        for r in records:
            vec = r["face_vector"]
            if isinstance(vec, str):
                vec = json.loads(vec)
            key = f"patient_{r['patient_id']}_{r['face_id']}"
            result[key] = vec
        if result:
            _embedding_cache = result
            _embedding_cache_ts = time.monotonic()
        return result
    except Exception as e:
        logger.warning("server face embeddings unavailable: %s", e)
        return _embedding_cache  # 만료된 캐시라도 반환


def invalidate_embedding_cache():
    """얼굴 등록 후 즉시 재조회 강제."""
    global _embedding_cache, _embedding_cache_ts
    _embedding_cache = {}
    _embedding_cache_ts = 0.0


def authenticate(face_img, threshold=FACE_MATCH_THRESHOLD, expected_user=None):
    try:
        embedding = get_embedding(face_img)
    except Exception:
        return None, -1

    db = _load_server() or _load_local()
    if not db:
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
