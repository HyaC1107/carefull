# utils/alert.py

import os

def alert_user():
    print("[알림] 복약 시간입니다!")

    # 🔔 소리 (Windows)
    try:
        print("알림중~")
    except:
        pass