from PyQt5.QtCore import QThread, pyqtSignal

from config.settings import UI_TEST_MODE


class FingerprintEnrollThread(QThread):
    """R307 지문 등록 스레드.

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
        self.stage_changed.emit("첫 번째 지문을 올려주세요")
        self.progress.emit(10)
        time.sleep(1.5)
        if not self._running:
            return
        self.progress.emit(40)
        time.sleep(0.5)
        if not self._running:
            return
        self.stage_changed.emit("손가락을 떼고 다시 올려주세요")
        self.progress.emit(50)
        time.sleep(1.5)
        if not self._running:
            return
        self.progress.emit(90)
        time.sleep(0.5)
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
                # ── 1단계: 첫 번째 지문 스캔 ─────────────────────────────
                self.stage_changed.emit("손가락을 올려주세요")
                self.progress.emit(10)

                while self._running:
                    if sensor.readImage():
                        break
                    self.msleep(100)
                if not self._running:
                    return

                sensor.convertImage(0x01)
                self.progress.emit(40)

                # ── 잠시 대기 ────────────────────────────────────────────
                self.stage_changed.emit("손가락을 떼고 다시 올려주세요")
                self.progress.emit(50)

                for _ in range(30):
                    if not self._running:
                        return
                    self.msleep(100)

                # ── 2단계: 두 번째 지문 스캔 ─────────────────────────────
                self.stage_changed.emit("같은 손가락을 다시 올려주세요")
                self.progress.emit(60)

                while self._running:
                    if sensor.readImage():
                        break
                    self.msleep(100)
                if not self._running:
                    return

                sensor.convertImage(0x02)
                self.progress.emit(80)

                # ── 3단계: 템플릿 생성 및 저장 ───────────────────────────
                if not sensor.createTemplate():
                    # 불일치 → 처음부터 재시도
                    self.stage_changed.emit("인식이 달라요. 다시 손가락을 올려주세요")
                    self.progress.emit(0)
                    self.msleep(1500)
                    continue

                sensor.storeTemplate(self._position)
                self.progress.emit(100)
                self.enrolled.emit(self._position)
                return

        except Exception as e:
            self.failed.emit(str(e))

    def stop(self):
        self._running = False


class FingerprintSearchThread(QThread):
    """R307 지문 인증 스레드.

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
