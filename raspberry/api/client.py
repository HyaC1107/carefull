import logging
import os
from datetime import datetime

import requests

from config.settings import API_BASE_URL, API_TIMEOUT, DEVICE_UID

logger = logging.getLogger(__name__)


def _url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}{path}"


def _log_error(context: str, exc: Exception) -> None:
    """HTTP 응답이 있으면 상태 코드 포함해서 로깅."""
    response = getattr(exc, "response", None)
    if response is not None:
        logger.error("%s failed: HTTP %s", context, response.status_code)
    else:
        logger.error("%s failed: %s", context, exc)


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


def fetch_device_status(device_uid: str = DEVICE_UID) -> dict:
    """기기 페어링 여부와 얼굴 등록 여부를 반환한다.

    Returns:
        {"is_paired": bool, "has_face": bool}
        - is_paired: 웹 대시보드에서 기기에 환자가 연결되어 있는지
        - has_face: 해당 기기에 얼굴 임베딩이 1건 이상 등록되어 있는지
    """
    result = {"is_paired": False, "has_face": False}
    if not device_uid:
        return result

    try:
        r = requests.post(
            _url("/api/device/ping"),
            json={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        if r.status_code == 200:
            device = r.json().get("device", {})
            result["is_paired"] = device.get("patient_id") is not None
    except Exception as e:
        logger.warning("fetch_device_status ping failed: %s", e)
        return result

    if result["is_paired"]:
        try:
            r = requests.get(
                _url("/api/face-data/device"),
                params={"device_uid": device_uid},
                timeout=API_TIMEOUT,
            )
            if r.status_code == 200:
                embeddings = r.json().get("face_embeddings", [])
                result["has_face"] = len(embeddings) > 0
        except Exception as e:
            logger.warning("fetch_device_status face check failed: %s", e)

    return result


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
        _log_error("send_device_event", e)
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
        _log_error("fetch_schedules", e)
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
        _log_error("fetch_face_embeddings", e)
        return []


def upload_fingerprint_id(fingerprint_id: int, device_uid: str = DEVICE_UID) -> bool:
    """하위 호환 유지 — 새 코드는 upload_fingerprint() 사용 권장."""
    return upload_fingerprint(fingerprint_id, device_uid=device_uid)


def upload_fingerprint(slot_id: int, label: str = "지문", device_uid: str = DEVICE_UID) -> bool:
    """새 지문 슬롯을 서버 fingerprints 테이블에 등록."""
    if not device_uid:
        logger.error("upload_fingerprint: DEVICE_UID not set")
        return False
    try:
        r = requests.post(
            _url("/api/device/fingerprints"),
            json={"device_uid": device_uid, "slot_id": slot_id, "label": label},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        _log_error("upload_fingerprint", e)
        return False


def fetch_fingerprints(device_uid: str = DEVICE_UID) -> list:
    """서버에 등록된 지문 슬롯 목록 조회."""
    if not device_uid:
        return []
    try:
        r = requests.get(
            _url("/api/device/fingerprints"),
            params={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        return r.json().get("fingerprints", [])
    except Exception as e:
        logger.error("fetch_fingerprints failed: %s", e)
        return []


def delete_fingerprint(slot_id: int, device_uid: str = DEVICE_UID) -> bool:
    """서버에서 특정 슬롯의 지문 레코드 삭제."""
    if not device_uid:
        return False
    try:
        r = requests.delete(
            _url(f"/api/device/fingerprints/{slot_id}"),
            params={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        return r.status_code == 200
    except Exception as e:
        logger.error("delete_fingerprint failed: %s", e)
        return False


def fetch_sound_meta(device_uid: str = DEVICE_UID) -> dict | None:
    """서버에서 현재 알림음 메타 조회. 파일 없으면 None 반환."""
    if not device_uid:
        return None
    try:
        r = requests.get(
            _url("/api/device/sound"),
            params={"device_uid": device_uid},
            timeout=API_TIMEOUT,
        )
        r.raise_for_status()
        sound = r.json().get("sound")
        if sound and sound.get("file_path"):
            sound["url"] = f"{API_BASE_URL.rstrip('/')}/{sound['file_path'].replace(os.sep, '/')}"
        return sound
    except Exception as e:
        logger.warning("fetch_sound_meta failed: %s", e)
        return None


def download_sound(url: str, dest_path: str) -> bool:
    """url에서 음원 파일을 dest_path로 다운로드."""
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        _log_error("download_sound", e)
        return False


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
        _log_error("upload_face_embedding", e)
        return False
