import json
import os
from datetime import datetime

from config.settings import DB_DIR

LOG_PATH = os.path.join(DB_DIR, "log_db.json")


def save_log(user, status):
    log = {
        "user": user,
        "status": status,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []

    data.append(log)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("[LOG SAVED]")
