import json
import os
from datetime import datetime

from raspberry.config.settings import DB_DIR

SCHEDULE_PATH = os.path.join(DB_DIR, "schedule.json")
last_triggered = {}


def check_schedule():
    now = datetime.now()
    now_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    try:
        with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
            schedules = json.load(f)
    except Exception:
        return []

    due_users = []

    for schedule in schedules:
        key = f"{schedule['user']}_{schedule['time']}"
        if schedule["time"] == now_time and last_triggered.get(key) != today:
            due_users.append(schedule["user"])
            last_triggered[key] = today

    return due_users
