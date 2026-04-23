import logging
from datetime import datetime

import requests

from config.settings import API_BASE_URL, API_TIMEOUT, DEVICE_UID

logger = logging.getLogger(__name__)


def _url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def ping_device(device_uid: str = DEVICE_UID) -> bool:
    if not device_uid:
        return False
    try:
        r = requests.post(
            _url("/api/device/ping"),
            json={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        return r.status_code == 200
    except Exception as e:
        logger.warning("ping failed: %s", e)
        return False


def send_device_event(
    sche_id: int,
    face_verified: bool,
    dispensed: bool,
    action_verified: bool,
    raw_confidence: float = 0.0,
    event_time: str = None,
    error_code: str = None,
    device_uid: str = DEVICE_UID,
) -> dict:
    if not device_uid:
        logger.error("send_device_event: CAREFULL_DEVICE_UID not set")
        return None

    payload = {
        "device_uid": device_uid,
        "sche_id": sche_id,
        "face_verified": face_verified,
        "dispensed": dispensed,
        "action_verified": action_verified,
        "raw_confidence": raw_confidence,
        "event_time": event_time or datetime.now().isoformat(),
    }
    if error_code:
        payload["error_code"] = error_code

    try:
        r = requests.post(_url("/api/log/device-event"), json=payload, timeout=API_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error("send_device_event failed: %s", e)
        return None


def fetch_schedules(device_uid: str = DEVICE_UID) -> list:
    if not device_uid:
        return []
    try:
        r = requests.get(
            _url("/api/schedule/device"),
            params={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("schedules", [])
    except Exception as e:
        logger.error("fetch_schedules failed: %s", e)
        return []


def fetch_face_embeddings(device_uid: str = DEVICE_UID) -> list:
    if not device_uid:
        return []
    try:
        r = requests.get(
            _url("/api/face-data/device"),
            params={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("face_embeddings", [])
    except Exception as e:
        logger.error("fetch_face_embeddings failed: %s", e)
        return []


def upload_face_embedding(face_vector: list, device_uid: str = DEVICE_UID) -> bool:
    if not device_uid:
        logger.error("upload_face_embedding: CAREFULL_DEVICE_UID not set")
        return False
    try:
        r = requests.post(
            _url("/api/face-data/device"),
            json={"device_uid": device_uid, "face_vector": face_vector},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error("upload_face_embedding failed: %s", e)
        return False
