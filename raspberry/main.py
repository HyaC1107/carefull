import os

# .env 파일이 있으면 자동 로드 (PC 테스트 시 .env.pc → .env 복사해서 사용)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from ui.app import run

if __name__ == "__main__":
    run()
