import json
import logging
import os
from datetime import datetime

from config.settings import DB_DIR

logger = logging.getLogger(__name__)

SCHEDULE_CACHE_PATH = os.path.join(DB_DIR, "schedule.json")
last_triggered: dict = {}


def _to_hhmm(time_val) -> str:
    """HH:MM:SS 또는 HH:MM → HH:MM 반환."""
    return str(time_val)[:5]


def sync_schedules() -> list:
    """백엔드에서 스케줄을 가져와 로컬 캐시에 저장. 실패하면 빈 리스트 반환."""
    from api.client import fetch_schedules
    schedules = fetch_schedules()
    if schedules is not None:
        # 빈 리스트여도 캐시를 덮어써서 이전 스케줄이 남지 않게 한다
        try:
            with open(SCHEDULE_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(schedules, f, ensure_ascii=False, default=str, indent=2)
        except Exception as e:
            logger.warning("schedule cache write failed: %s", e)
    return schedules or []


def _load_cached() -> list:
    try:
        with open(SCHEDULE_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def check_schedule(schedules: list = None) -> list:
    """현재 시각에 맞는 스케줄 목록 반환 (중복 트리거 방지)."""
    now = datetime.now()
    now_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    if schedules is None:
        schedules = _load_cached()

    due = []
    for s in schedules:
        sche_id = s.get("sche_id") or s.get("user")
        time_val = s.get("time_to_take") or s.get("time", "")
        sche_time = _to_hhmm(time_val)

        key = f"{sche_id}_{sche_time}"
        if sche_time == now_time and last_triggered.get(key) != today:
            due.append(s)
            last_triggered[key] = today

    return due
