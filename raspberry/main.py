import os
import sys
import logging
from raspberry.config.settings import BASE_DIR, ENV_DIR
from ui.app import run

# 로깅 설정 (프로그램이 실행되는 동안 일어나는 일들을 기록하는 '일기장'을 설정)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Main")

# 프로젝트 루트 경로 추가 (부모 디렉토리인 raspberry를 모듈로 인식하게 함)
sys.path.append(BASE_DIR)

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv(ENV_DIR)
except ImportError:
    from ui.app import run
    from hardware.manager import HardwareManager

    if __name__ == "__main__":
        try:
            logger.info("Starting Carefull Raspberry Pi Application")

            # 1. 하드웨어 초기화
            if not HardwareManager.initialize():
                logger.error("Failed to initialize hardware. Exiting.")
                sys.exit(1)

            # 2. 자가 진단 (필요 시)
            HardwareManager.self_test()

            # 3. UI 및 메인 루프 실행
            run()

        except KeyboardInterrupt:
            logger.info("Application stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            # 4. 리소스 정리
            HardwareManager.cleanup()

