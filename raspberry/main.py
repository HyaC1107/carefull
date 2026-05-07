import os
import sys
import logging
from config.settings import BASE_DIR, ENV_DIR
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

from hardware.Controller import Controller
from camera.camera import check_camera_health, release_camera


def _kill_stray_camera_processes():
    """이전 앱 종료 시 해제되지 않은 libcamera 좀비 프로세스를 정리."""
    import subprocess, os
    current_pid = os.getpid()
    try:
        result = subprocess.run(
            ["pgrep", "-f", "libcamera"],
            capture_output=True, text=True
        )
        for pid_str in result.stdout.strip().splitlines():
            pid = int(pid_str)
            if pid != current_pid:
                subprocess.run(["kill", "-9", str(pid)], capture_output=True)
                logger.info(f"Killed stray libcamera process: {pid}")
    except Exception:
        pass


if __name__ == "__main__":
    controller = None
    try:
        logger.info("Starting Carefull Raspberry Pi Application")

        # 1. 하드웨어 및 시스템 컨트롤러 인스턴스 생성
        controller = Controller()

        # 2. 하드웨어 초기화 (GPIO 설정 등)
        if not controller.initialize_hardware():
            logger.error("Failed to initialize hardware. Exiting.")
            sys.exit(1)

        # 3. 카메라 점검 (이전 좀비 프로세스 정리 후 시도)
        _kill_stray_camera_processes()
        camera_ok = check_camera_health()
        if not camera_ok:
            # 파이프라인이 해제될 시간을 주고 한 번 더 시도
            logger.warning("Camera health check failed, retrying after 2s...")
            import time as _t; _t.sleep(2)
            release_camera()
            camera_ok = check_camera_health()

        if camera_ok:
            logger.info("Camera health check passed.")
        else:
            logger.warning("Camera health check failed! Please check the camera connection.")

        # 점검 후 카메라 리소스 해제 (UI에서 필요할 때 다시 켬)
        release_camera()

        # 4. 자가 진단 (카메라 재초기화 없이 위 결과 전달)
        controller.self_test(camera_ok=camera_ok)

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

        Controller.cleanup_hardware()
        release_camera() # 종료 시 카메라 확실히 해제
        logger.info("Application resources cleaned up and exited.")
