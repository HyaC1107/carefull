import time
from pyfingerprint.pyfingerprint import PyFingerprint

# 라즈베리파이 설정법
# 1. sudo raspi-config > interface > enable (재부팅)
# 2-1. sudo nano /boot/firmware/cmdline.txt
# 2-2. 내용 중에 console=serial0,115200 또는 console=ttyS0,115200 문구 있다면 지우기

# 지문 등록
# python3 ../dev_test/actuator/fingerprintTest.py enroll 1 (1번에)
# 지문 확인
# python3 dev_test/actuator/fingerprintTest.py search

def get_sensor():
    """센서 객체를 초기화해서 반환하는 내부 함수"""
    try:
        # sudo ls -l /dev/serial* 로 tty50찾아야함
        f = PyFingerprint('/dev/serial0', 57600, address=0xFFFFFFFF)
        if not f.verifyPassword():
            raise Exception("센서 비밀번호가 틀렸어!")
        return f
    except Exception as e:
        print(f"센서 연결 실패: {e}")
        return None

def fingerprint_search():
    """지문 스캔 후 (ID, score) 튜플 반환. 미등록이면 (-1, 0)."""
    f = get_sensor()
    if not f: return None

    print("손가락을 올려줘...")
    while not f.readImage(): pass

    f.convertImage(0x01)
    result = f.searchTemplate()
    positionNumber = result[0]
    accuracyScore = result[1]

    return positionNumber, accuracyScore

def fingerprint_enroll(position):
    """
    새로운 지문을 특정 위치(ID)에 등록
    :param position: 저장할 ID 번호 (0~1000 등)
    """
    f = get_sensor()
    if not f: return False

    try:
        # 1. 첫 번째 지문 스캔
        print(f"ID #{position} 등록을 시작할게. 손가락을 올려줘!")
        while not f.readImage(): pass
        f.convertImage(0x01)
        print("첫 번째 스캔 완료. 손가락을 떼고 잠시만 기다려줘.")
        
        time.sleep(2)
        print("다시 한번 똑같은 손가락을 올려줘!")
        
        # 2. 두 번째 지문 스캔 (확인용)
        while not f.readImage(): pass
        f.convertImage(0x02)
        print("두 번째 스캔 완료.")

        # 3. 두 지문 비교해서 모델 생성
        if f.createTemplate():
            print("두 지문이 일치해! 모델을 생성했어.")
        else:
            print("지문이 서로 달라. 다시 시도해줘.")
            return False

        # 4. 특정 위치에 저장
        f.storeTemplate(position)
        print(f"성공! ID #{position}에 지문이 등록되었어.")
        return True

    except Exception as e:
        print(f"등록 중 에러 발생: {e}")
        return False

# --- 직접 실행 테스트 ---
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  검색: python3 fingerprint.py search")
        print("  등록: python3 fingerprint.py enroll [ID번호]")
        sys.exit()

    mode = sys.argv[1]
    
    if mode == "search":
        res = fingerprint_search()
        if res is None:
            print("센서 연결 오류")
        elif res[0] == -1:
            print("누구신지...? 등록되지 않은 지문이야.")
        else:
            print(f"확인됨! ID: {res[0]}, Score: {res[1]}")
        
    elif mode == "enroll" and len(sys.argv) > 2:
        target_id = int(sys.argv[2])
        fingerprint_enroll(target_id)
    else:
        print("인자를 정확히 입력해줘!")