import json
import os
from datetime import datetime

class ScheduleManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.schedules = []
        self.load_schedules()

    def load_schedules(self):
        """JSON 파일에서 스케줄을 로드합니다."""
        if not os.path.exists(self.db_path):
            print(f"[ERROR] DB file not found: {self.db_path}")
            return
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                self.schedules = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load schedules: {e}")

    def get_upcoming_schedule(self):
        """현재 시각 이후에 가장 가까운 스케줄을 반환합니다."""
        now = datetime.now().strftime("%H:%M")
        # 시간순 정렬
        sorted_schedules = sorted(self.schedules, key=lambda x: x.get('time_to_take', '00:00'))
        
        for s in sorted_schedules:
            if s.get('time_to_take') > now:
                return s
        
        # 오늘 남은 게 없으면 내일 첫 번째 스케줄
        return sorted_schedules[0] if sorted_schedules else None

    def check_now_schedule(self):
        """현재 시각에 복약해야 할 스케줄이 있는지 확인합니다."""
        now = datetime.now().strftime("%H:%M")
        for s in self.schedules:
            if s.get('time_to_take') == now:
                return s
        return None

if __name__ == "__main__":
    # 테스트 코드
    db_file = os.path.join(os.path.dirname(__file__), "../../raspberry/db/schedule.json")
    manager = ScheduleManager(db_file)
    print("전체 스케줄:", manager.schedules)
    
    upcoming = manager.get_upcoming_schedule()
    if upcoming:
        print(f"다음 예정 복약: {upcoming['time_to_take']} ({upcoming['medication_name']})")
    
    now_sche = manager.check_now_schedule()
    if now_sche:
        print(f"!!! 지금 복약 시간입니다: {now_sche['medication_name']} !!!")
    else:
        print("현재 시각에 예정된 복약이 없습니다.")
