#!/usr/bin/env python3
"""
개발용 핫 리로드 — ui/ config/ 폴더의 .py/.qss 파일 변경 시 앱 자동 재시작.

사용법:
    pip install watchdog        # 최초 1회
    python dev_watch.py

파일 저장하면 약 1초 후 자동 재시작됨.
종료: Ctrl+C
"""
import subprocess
import sys
import time
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("[dev_watch] watchdog 패키지가 없습니다: pip install watchdog")
    sys.exit(1)

WATCH_DIRS = ["ui", "config", "hardware", "scheduler"]
WATCH_EXTS = {".py", ".qss"}
DEBOUNCE_SEC = 0.8          # 연속 저장 시 중복 재시작 방지
BASE = Path(__file__).parent


class _ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self._last_trigger = 0.0
        self.pending = False

    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).suffix in WATCH_EXTS:
            now = time.time()
            if now - self._last_trigger >= DEBOUNCE_SEC:
                self._last_trigger = now
                self.pending = True
                rel = Path(event.src_path).relative_to(BASE) if BASE in Path(event.src_path).parents else event.src_path
                print(f"\n[dev_watch] 변경 감지: {rel}")

    on_created = on_modified


def _start_app() -> subprocess.Popen:
    return subprocess.Popen([sys.executable, str(BASE / "main.py")])


def main():
    handler = _ChangeHandler()
    observer = Observer()
    for d in WATCH_DIRS:
        p = BASE / d
        if p.exists():
            observer.schedule(handler, str(p), recursive=True)
            print(f"[dev_watch] 감시: {p}")

    observer.start()
    proc = _start_app()
    print("[dev_watch] 앱 시작 완료. 파일을 저장하면 자동 재시작됩니다. (종료: Ctrl+C)\n")

    try:
        while True:
            time.sleep(0.3)
            if handler.pending:
                handler.pending = False
                print("[dev_watch] 재시작 중...")
                proc.terminate()
                try:
                    proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    proc.kill()
                time.sleep(0.4)
                proc = _start_app()
                print("[dev_watch] 재시작 완료.\n")
    except KeyboardInterrupt:
        print("\n[dev_watch] 종료합니다.")
        proc.terminate()
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
