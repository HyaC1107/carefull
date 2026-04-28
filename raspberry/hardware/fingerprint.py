import time
import logging
from pyfingerprint.pyfingerprint import PyFingerprint

logger = logging.getLogger("Fingerprint")

# 라즈베리파이 설정법
# 1. sudo raspi-config > interface > enable (재부팅)
# 2-1. sudo nano /boot/firmware/cmdline.txt
# 2-2. 내용 중에 console=serial0,115200 또는 console=ttyS0,115200 문구 있다면 지우기

# 지문 등록
# python3 ../dev_test/actuator/fingerprintTest.py enroll 1 (1번에)
# 지문 확인
# python3 dev_test/actuator/fingerprintTest.py search

class FingerprintManager:
    def __init__(self, device='/dev/serial0', baud=57600):
        self.device = device
        self.baud = baud
        self.sensor = self._connect()

    def _connect(self):
        """센서 객체를 초기화해서 반환"""
        try:
            f = PyFingerprint(self.device, self.baud, address=0xFFFFFFFF)
            if not f.verifyPassword():
                raise Exception("센서 비밀번호가 틀렸습니다.")
            logger.info("Fingerprint sensor connected successfully.")
            return f
        except Exception as e:
            logger.error(f"Fingerprint sensor connection failed: {e}")
            return None

    def search(self):
        """
        지문 스캔 후 (ID, score) 튜플 반환. 
        미등록 또는 실패 시 (-1, 0).
        """
        if not self.sensor:
            logger.error("Sensor not initialized.")
            return -1, 0

        try:
            logger.info("Waiting for finger...")
            # 센서가 지문을 읽을 때까지 대기 (UI에서 사용 시 Non-blocking 고려 필요)
            while not self.sensor.readImage():
                time.sleep(0.1)

            self.sensor.convertImage(0x01)
            result = self.sensor.searchTemplate()
            
            position_number = result[0]
            accuracy_score = result[1]

            logger.info(f"Fingerprint found: ID #{position_number} (Score: {accuracy_score})")
            return position_number, accuracy_score

        except Exception as e:
            logger.error(f"Error during fingerprint search: {e}")
            return -1, 0

    def enroll(self, position):
        """
        새로운 지문을 특정 위치(ID)에 등록
        :param position: 저장할 ID 번호 (0~1000 등)
        """
        if not self.sensor:
            logger.error("Sensor not initialized.")
            return False

        try:
            # 1. 첫 번째 지문 스캔
            logger.info(f"Enroll start for ID #{position}. Place finger.")
            while not self.sensor.readImage():
                time.sleep(0.1)
            self.sensor.convertImage(0x01)
            
            logger.info("First scan done. Remove finger.")
            time.sleep(2)
            
            # 2. 두 번째 지문 스캔 (확인용)
            logger.info("Place the same finger again.")
            while not self.sensor.readImage():
                time.sleep(0.1)
            self.sensor.convertImage(0x02)

            # 3. 두 지문 비교해서 모델 생성
            if self.sensor.createTemplate():
                logger.info("Templates match! Creating model.")
            else:
                logger.warning("Templates do not match.")
                return False

            # 4. 특정 위치에 저장
            self.sensor.storeTemplate(position)
            logger.info(f"Successfully enrolled to ID #{position}.")
            return True

        except Exception as e:
            logger.error(f"Error during fingerprint enrollment: {e}")
            return False

# 싱글톤 패턴 또는 글로벌 인스턴스로 사용 가능
_instance = None

def get_fingerprint_manager():
    global _instance
    if _instance is None:
        _instance = FingerprintManager()
    return _instance
