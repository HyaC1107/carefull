import os

from PyQt5.QtCore import Qt, QThread, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

def _play_voice(filename: str):
    try:
        from hardware.alarm import play_voice
        play_voice(filename)
    except Exception:
        pass


_MAX_FINGERS = 3   # 최대 등록 가능한 손가락 수

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG     = "#F5EBFF"
_PURPLE = "#7c3aed"
_DARK   = "#1e1b4b"
_GREEN  = "#16a34a"


class _UploadWorker(QThread):
    def __init__(self, fp_id: int, label: str = "지문", parent=None):
        super().__init__(parent)
        self._fp_id  = fp_id
        self._label  = label

    def run(self):
        try:
            from api.client import upload_fingerprint
            upload_fingerprint(self._fp_id, label=self._label)
        except Exception as e:
            print(f"[FP UPLOAD ERROR] {e}")


class _FingerprintWidget(QWidget):
    """지문 아이콘 (동심 호 + 어두운 배경 카드)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self.setFixedSize(220, 220)

    def set_progress(self, pct: int):
        self._progress = max(0, min(100, pct))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()

        p.setBrush(QColor("#1e1535"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 20, 20)

        cx, cy = w / 2, h / 2

        arcs = [
            (14,  -30 * 16, 240 * 16),
            (23,  -40 * 16, 260 * 16),
            (33,  -50 * 16, 280 * 16),
            (43,  -55 * 16, 290 * 16),
            (52,  -55 * 16, 290 * 16),
            (62,  -50 * 16, 280 * 16),
            (72,  -40 * 16, 250 * 16),
        ]
        for i, (r, start, span) in enumerate(arcs):
            arc_alpha = min(255, 60 + int((self._progress / 100) * 195) + i * 10)
            c = QColor(_PURPLE)
            c.setAlpha(arc_alpha)
            pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                start, span,
            )


class FingerprintRegisterScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app            = parent
        self._fp_id          = None
        self._thread         = None
        self._prepare_thread = None
        self._upload_workers = []   # 진행 중 업로드 워커 보관 (GC 방지)
        self._finger_count   = 0    # 이번 세션에서 등록 완료된 손가락 수
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(f"FingerprintRegisterScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 0, 24, 24)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        root.addStretch(2)

        # ── 지문 아이콘 ──────────────────────────────────────────────────────
        _fp_path = os.path.join(_ICONS_DIR, "fingerprint.png")
        if os.path.exists(_fp_path):
            self._fp_widget = QLabel()
            self._fp_widget.setAlignment(Qt.AlignCenter)
            _pix = QPixmap(_fp_path).scaled(240, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._fp_widget.setPixmap(_pix)
        else:
            self._fp_widget = _FingerprintWidget()
        root.addWidget(self._fp_widget, alignment=Qt.AlignCenter)
        root.addSpacing(20)

        # ── 진행바 ───────────────────────────────────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setFixedWidth(600)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background: #d8b4fe;
            }}
            QProgressBar::chunk {{
                background-color: {_PURPLE};
                border-radius: 4px;
            }}
        """)
        _prog_row = QHBoxLayout()
        _prog_row.addStretch()
        _prog_row.addWidget(self._progress_bar)
        _prog_row.addStretch()
        root.addLayout(_prog_row)
        root.addSpacing(16)

        # ── 안내 텍스트 ──────────────────────────────────────────────────────
        self._title_lbl = QLabel("준비 중...")
        self._title_lbl.setFont(QFont("Sans Serif", 42, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._title_lbl)

        root.addSpacing(8)

        self._sub_lbl = QLabel("센서에 손가락을 올려주세요")
        self._sub_lbl.setFont(QFont("Sans Serif", 30))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setStyleSheet(f"color: {_PURPLE};")
        root.addWidget(self._sub_lbl)

        root.addSpacing(8)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(QFont("Sans Serif", 32, QFont.Bold))
        self._pct_lbl.setAlignment(Qt.AlignCenter)
        self._pct_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._pct_lbl)

        root.addSpacing(20)

        # ── 오류 + 재시도 위젯 ───────────────────────────────────────────────
        self._error_widget = QWidget()
        self._error_widget.setStyleSheet("""
            QWidget {
                background-color: #fff1f2;
                border: 2px solid #fecaca;
                border-radius: 16px;
            }
        """)
        error_layout = QVBoxLayout(self._error_widget)
        error_layout.setContentsMargins(20, 16, 20, 16)
        error_layout.setSpacing(12)

        self._error_lbl = QLabel("")
        self._error_lbl.setFont(QFont("Sans Serif", 28, QFont.Bold))
        self._error_lbl.setAlignment(Qt.AlignCenter)
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setStyleSheet("color: #dc2626; border: none; background: transparent;")
        error_layout.addWidget(self._error_lbl)

        self._btn_retry = QPushButton("다시 시도")
        self._btn_retry.setFont(QFont("Sans Serif", 28, QFont.Bold))
        self._btn_retry.setFixedHeight(72)
        self._btn_retry.setStyleSheet(f"""
            QPushButton {{
                background-color: #dc2626;
                color: white;
                border-radius: 16px;
                border: none;
            }}
            QPushButton:pressed {{ background-color: #b91c1c; }}
        """)
        self._btn_retry.clicked.connect(self._on_retry)
        error_layout.addWidget(self._btn_retry)

        self._error_widget.hide()
        root.addWidget(self._error_widget)

        root.addSpacing(20)

        # ── 다손가락 등록 프롬프트 (등록 완료 후 표시) ──────────────────────
        self._prompt_widget = QWidget()
        self._prompt_widget.setStyleSheet(f"""
            QWidget {{
                background-color: #f5f3ff;
                border: 2px solid #c4b5fd;
                border-radius: 16px;
            }}
        """)
        prompt_layout = QVBoxLayout(self._prompt_widget)
        prompt_layout.setContentsMargins(20, 16, 20, 16)
        prompt_layout.setSpacing(14)

        self._prompt_lbl = QLabel("다른 손가락도 등록할까요?")
        self._prompt_lbl.setFont(QFont("Sans Serif", 34, QFont.Bold))
        self._prompt_lbl.setAlignment(Qt.AlignCenter)
        self._prompt_lbl.setStyleSheet(f"color: {_DARK}; border: none; background: transparent;")
        prompt_layout.addWidget(self._prompt_lbl)

        self._prompt_sub_lbl = QLabel("")
        self._prompt_sub_lbl.setFont(QFont("Sans Serif", 26))
        self._prompt_sub_lbl.setAlignment(Qt.AlignCenter)
        self._prompt_sub_lbl.setStyleSheet(f"color: {_PURPLE}; border: none; background: transparent;")
        prompt_layout.addWidget(self._prompt_sub_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(20)
        btn_row.setContentsMargins(60, 0, 60, 0) # 버튼 가로 폭 조절

        self._btn_more = QPushButton("다른 손가락 등록")
        self._btn_more.setFont(QFont("Sans Serif", 26, QFont.Bold))
        self._btn_more.setFixedHeight(80)
        self._btn_more.setStyleSheet(f"""
            QPushButton {{
                background-color: {_PURPLE};
                color: white;
                border-radius: 18px;
                border: none;
            }}
            QPushButton:pressed {{ background-color: #6d28d9; }}
        """)
        self._btn_more.clicked.connect(self._on_more_finger)

        self._btn_done = QPushButton("등록 완료")
        self._btn_done.setFont(QFont("Sans Serif", 26))
        self._btn_done.setFixedHeight(80)
        self._btn_done.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {_GREEN};
                border-radius: 18px;
                border: 2.5px solid {_GREEN};
            }}
            QPushButton:pressed {{ background-color: #f0fdf4; }}
        """)
        self._btn_done.clicked.connect(self._go_complete)

        btn_row.addWidget(self._btn_more, 1) # 1:1 비율
        btn_row.addWidget(self._btn_done, 1)
        prompt_layout.addLayout(btn_row)

        self._prompt_widget.hide()
        root.addWidget(self._prompt_widget)

        root.addStretch(2)

    # ── 생명주기 ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._finger_count = 0
        self._reset()
        self._prepare_slot()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_thread()

    # ── 내부 로직 ─────────────────────────────────────────────────────────────

    def _reset(self):
        self._progress_bar.setValue(0)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(0)
        self._pct_lbl.setText("0%")
        self._title_lbl.setText("준비 중...")
        self._prompt_widget.hide()
        self._error_widget.hide()

    def _prepare_slot(self):
        """서버에서 기존 슬롯 조회 후 다음 빈 슬롯 번호 확정."""
        from ui.threads.fingerprint_thread import FingerprintPrepareThread
        self._prepare_thread = FingerprintPrepareThread(parent=self)
        self._prepare_thread.ready.connect(self._on_slot_ready)
        self._prepare_thread.start()

    def _on_slot_ready(self, next_slot: int):
        self._title_lbl.setText("손가락을 올려주세요")
        self._sub_lbl.setText(f"센서에 손가락을 올려주세요  ({self._finger_count + 1}번째)")
        _play_voice("reg_fp_start.mp3")
        self._start_enroll(next_slot)

    def _start_enroll(self, position: int = 1):
        self._stop_thread()
        from ui.threads.fingerprint_thread import FingerprintEnrollThread
        self._thread = FingerprintEnrollThread(position=position, parent=self)
        self._thread.stage_changed.connect(self._on_stage)
        self._thread.progress.connect(self._on_progress)
        self._thread.enrolled.connect(self._on_enrolled)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(2000)
        self._thread = None

    # ── 시그널 핸들러 ─────────────────────────────────────────────────────────

    def _on_stage(self, msg: str):
        self._title_lbl.setText(msg)
        if "떼주세요" in msg:
            _play_voice("reg_fp_lift.mp3")
        elif "다시 올려주세요" in msg or "번 더 올려주세요" in msg:
            _play_voice("reg_fp_again.mp3")
        elif "다시 시도합니다" in msg:
            _play_voice("reg_fp_error.mp3")

    def _on_progress(self, value: int):
        self._progress_bar.setValue(value)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(value)
        self._pct_lbl.setText(f"{value}%")

    def _on_enrolled(self, fp_id: int):
        self._finger_count += 1
        label = f"지문{self._finger_count}"

        # 서버 업로드 (비동기, GC 방지를 위해 목록에 보관)
        worker = _UploadWorker(fp_id, label=label, parent=self)
        self._upload_workers.append(worker)
        worker.start()

        self._title_lbl.setText(f"등록 완료! ({self._finger_count}번째 손가락)")
        self._on_progress(100)
        _play_voice("reg_fp_done.mp3")

        if self._finger_count < _MAX_FINGERS:
            QTimer.singleShot(700, self._show_prompt)
        else:
            QTimer.singleShot(700, self._go_complete)

    def _on_failed(self, msg: str):
        self._title_lbl.setText("등록 중 오류가 발생했습니다")
        self._sub_lbl.setText("")
        self._pct_lbl.setText("")
        self._error_lbl.setText(msg)
        self._error_widget.show()
        _play_voice("reg_fp_error.mp3")

    def _on_retry(self):
        self._reset()
        self._title_lbl.setText("다시 시도합니다...")
        self._sub_lbl.setText("센서에 손가락을 올려주세요")
        self._prepare_slot()

    # ── 다손가락 프롬프트 ─────────────────────────────────────────────────────

    def _show_prompt(self):
        remaining = _MAX_FINGERS - self._finger_count
        self._prompt_lbl.setText(f"다른 손가락도 등록할까요?")
        self._prompt_sub_lbl.setText(
            f"{self._finger_count}개 등록됨  •  최대 {remaining}개 더 등록 가능"
        )
        self._progress_bar.setValue(0)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(0)
        self._pct_lbl.setText("")
        self._prompt_widget.show()
        _play_voice("reg_fp_more.mp3")

    def _on_more_finger(self):
        self._prompt_widget.hide()
        self._sub_lbl.setText("센서에 손가락을 올려주세요")
        self._prepare_slot()

    # ── 완료 ─────────────────────────────────────────────────────────────────

    def _go_complete(self):
        if self._app:
            self._app.show_screen("register_complete")
