from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE


class FingerprintPrepareThread(QThread):
    """서버에서 기존 지문 슬롯 조회 후 다음 사용 가능한 슬롯 번호를 시그널로 전달."""
    ready = pyqtSignal(int)

    def run(self):
        next_slot = 1
        try:
            from api.client import fetch_fingerprints
            fps = fetch_fingerprints()
            used = {fp["slot_id"] for fp in fps}
            while next_slot in used:
                next_slot += 1
        except Exception:
            pass
        self.ready.emit(next_slot)


class FingerprintEnrollThread(QThread):
    """R307 지문 등록 스레드 (3-스캔 방식).

    flow:
        1차 스캔 → buf1
        2차 스캔 → buf2 → createTemplate 시도
          성공 → 저장
          실패 → 3차 스캔 → buf2 덮어쓰기 → createTemplate 재시도
                  성공 → 저장
                  실패 → 처음부터 재시작

    Signals:
        stage_changed(str): 현재 단계 안내 메시지
        progress(int):      0~100 진행률
        enrolled(int):      등록 성공 — 슬롯 ID 전달
        failed(str):        등록 실패 — 에러 메시지 전달
    """
    stage_changed = pyqtSignal(str)
    progress      = pyqtSignal(int)
    enrolled      = pyqtSignal(int)
    failed        = pyqtSignal(str)

    def __init__(self, position: int = 1, parent=None):
        super().__init__(parent)
        self._position = position
        self._running  = True

    def run(self):
        if UI_TEST_MODE:
            self._run_mock()
            return
        self._run_real()

    def _run_mock(self):
        import time
        self.stage_changed.emit("손가락을 올려주세요")
        self.progress.emit(10)
        time.sleep(1.5)
        if not self._running:
            return
        self.progress.emit(35)
        self.stage_changed.emit("손가락을 떼주세요")
        self.progress.emit(40)
        time.sleep(0.8)
        if not self._running:
            return
        self.stage_changed.emit("같은 손가락을 다시 올려주세요  (2/3)")
        self.progress.emit(50)
        time.sleep(1.5)
        if not self._running:
            return
        self.progress.emit(88)
        time.sleep(0.4)
        if not self._running:
            return
        self.progress.emit(100)
        self.enrolled.emit(self._position)

    def _run_real(self):
        try:
            from hardware.fingerprint import get_fingerprint_manager
            mgr = get_fingerprint_manager()
            if mgr.sensor is None:
                self.failed.emit("센서 연결 실패")
                return

            sensor = mgr.sensor

            while self._running:
                # ── 1차 스캔 → CharBuffer1 ──────────────────────────────────
                self.stage_changed.emit("손가락을 올려주세요")
                self.progress.emit(10)
                while self._running:
                    if sensor.readImage():
                        break
                    self.msleep(100)
                if not self._running:
                    return
                sensor.convertImage(0x01)
                self.progress.emit(35)

                # ── 1차 대기 ────────────────────────────────────────────────
                self.stage_changed.emit("손가락을 떼주세요")
                self.progress.emit(40)
                for _ in range(30):
                    if not self._running:
                        return
                    self.msleep(100)

                # ── 2차 스캔 → CharBuffer2 ──────────────────────────────────
                self.stage_changed.emit("같은 손가락을 다시 올려주세요  (2/3)")
                self.progress.emit(50)
                while self._running:
                    if sensor.readImage():
                        break
                    self.msleep(100)
                if not self._running:
                    return
                sensor.convertImage(0x02)
                self.progress.emit(65)

                # ── 1차 매칭 시도 ────────────────────────────────────────────
                if sensor.createTemplate():
                    sensor.storeTemplate(self._position)
                    self.progress.emit(100)
                    self.enrolled.emit(self._position)
                    return

                # ── 2차 대기 ────────────────────────────────────────────────
                self.stage_changed.emit("손가락을 떼주세요  (한 번 더 기회가 있어요)")
                self.progress.emit(70)
                for _ in range(20):
                    if not self._running:
                        return
                    self.msleep(100)

                # ── 3차 스캔 → CharBuffer2 덮어쓰기 ─────────────────────────
                self.stage_changed.emit("한 번 더 올려주세요  (3/3)")
                self.progress.emit(75)
                while self._running:
                    if sensor.readImage():
                        break
                    self.msleep(100)
                if not self._running:
                    return
                sensor.convertImage(0x02)
                self.progress.emit(88)

                # ── 2차 매칭 시도 ────────────────────────────────────────────
                if sensor.createTemplate():
                    sensor.storeTemplate(self._position)
                    self.progress.emit(100)
                    self.enrolled.emit(self._position)
                    return

                # 3번 모두 실패 → 처음부터 재시작
                self.stage_changed.emit("인식이 안됩니다. 처음부터 다시 시도합니다")
                self.progress.emit(0)
                self.msleep(2000)

        except Exception as e:
            self.failed.emit(str(e))

    def stop(self):
        self._running = False


class FingerprintSearchThread(QThread):
    """R307 지문 인증 스레드.
    searchTemplate() 이 센서 전체 슬롯을 탐색하므로
    여러 손가락이 등록되어 있어도 자동으로 1-of-N 매칭됩니다.

    Signals:
        found(int, int):  인증 성공 — (슬롯 ID, 정확도 점수)
        not_found():      등록되지 않은 지문
        failed(str):      오류
    """
    found     = pyqtSignal(int, int)
    not_found = pyqtSignal()
    failed    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True

    def run(self):
        if UI_TEST_MODE:
            self._run_mock()
            return
        self._run_real()

    def _run_mock(self):
        import time
        time.sleep(2)
        if self._running:
            self.found.emit(1, 200)

    def _run_real(self):
        try:
            from hardware.fingerprint import get_fingerprint_manager
            mgr = get_fingerprint_manager()
            if mgr.sensor is None:
                self.failed.emit("센서 연결 실패")
                return

            sensor = mgr.sensor

            while self._running:
                if sensor.readImage():
                    break
                self.msleep(100)
            if not self._running:
                return

            sensor.convertImage(0x01)
            result = sensor.searchTemplate()
            position, score = result[0], result[1]

            if position == -1:
                self.not_found.emit()
            else:
                self.found.emit(position, score)

        except Exception as e:
            self.failed.emit(str(e))

    def stop(self):
        self._running = False
