"""
기기 고유 ID 관리.

우선순위:
  1. 환경변수 CAREFULL_DEVICE_UID (수동 지정)
  2. db/device.json 에 저장된 값
  3. MAC 주소 기반 UUID5 자동 생성 후 db/device.json 저장
"""

import json
import os
import uuid

_DEVICE_JSON = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'db', 'device.json')
)


def get_device_uid() -> str:
    # 1. 환경변수 우선
    env_uid = os.getenv('CAREFULL_DEVICE_UID', '').strip()
    if env_uid:
        return env_uid

    # 2. 저장된 파일에서 읽기
    try:
        with open(_DEVICE_JSON, 'r', encoding='utf-8') as f:
            uid = json.load(f).get('device_uid', '').strip()
        if uid:
            return uid
    except Exception:
        pass

    # 3. MAC 주소 기반 UUID5 생성 (재부팅·파일 삭제 후에도 동일값 복원)
    uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid.getnode())))
    _save(uid)
    return uid


def _save(uid: str) -> None:
    os.makedirs(os.path.dirname(_DEVICE_JSON), exist_ok=True)
    try:
        with open(_DEVICE_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {}
    data['device_uid'] = uid
    with open(_DEVICE_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
