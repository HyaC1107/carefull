import os
import sys
import logging
from raspberry.config.settings import BASE_DIR, ENV_DIR
from ui.app import run

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("Main")

# 프로젝트 루트 경로 추가
sys.path.append(BASE_DIR)

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv(ENV_DIR)
except ImportError:
    pass

from hardware.SystemController import SystemController
from camera.camera import check_camera_health, release_camera

if __name__ == "__main__":
    controller = None
    try:
        logger.info("Starting Carefull Raspberry Pi Application")

        # 1. 하드웨어 및 시스템 컨트롤러 인스턴스 생성
        controller = SystemController()

        # 2. 하드웨어 초기화 (GPIO 설정 등)
        if not controller.initialize_hardware():
            logger.error("Failed to initialize hardware. Exiting.")
            sys.exit(1)

        # 3. 카메라 점검
        if check_camera_health():
            logger.info("Camera health check passed.")
        else:
            logger.warning("Camera health check failed! Please check the camera connection.")
        
        # 점검 후 카메라 리소스 해제 (UI에서 필요할 때 다시 켬)
        release_camera()

        # 4. 자가 진단
        controller.self_test()

        # 5. 백그라운드 스케줄 감시 시작
        controller.start()

        # 6. UI 및 메인 루프 실행
        run()

    except KeyboardInterrupt:
        logger.info("Application stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
    finally:
        # 7. 리소스 정리
        if controller:
            controller.stop()
        
        SystemController.cleanup_hardware()
        release_camera() # 종료 시 카메라 확실히 해제
        logger.info("Application resources cleaned up and exited.")
