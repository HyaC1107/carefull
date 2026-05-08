import os

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_BG    = "#F5EBFF"
_BLUE  = "#3b82f6"
_DARK  = "#1e3a5f"
_RED   = "#ef4444"

_AUTH_TIMEOUT_MS = 30_000
_MAX_RETRIES     = 3


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

        p.setBrush(QColor("#0f1e3a"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, w, h, 20, 20)

        cx, cy = w / 2, h / 2

        arcs = [
            (14, -30 * 16, 240 * 16),
            (23, -40 * 16, 260 * 16),
            (33, -50 * 16, 280 * 16),
            (43, -55 * 16, 290 * 16),
            (52, -55 * 16, 290 * 16),
            (62, -50 * 16, 280 * 16),
            (72, -40 * 16, 250 * 16),
        ]
        for i, (r, start, span) in enumerate(arcs):
            arc_alpha = min(255, 60 + int((self._progress / 100) * 195) + i * 10)
            c = QColor(_BLUE)
            c.setAlpha(arc_alpha)
            pen = QPen(c, 2.5, Qt.SolidLine, Qt.RoundCap)
            p.setPen(pen)
            p.drawArc(
                QRectF(cx - r, cy - r, r * 2, r * 2),
                start, span,
            )


class FingerprintAuthScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app           = parent
        self._thread        = None
        self._timeout_timer = None
        self._retry_count   = 0
        self._build_ui()

    # ── UI 구성 ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"FingerprintAuthScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(120, 20, 120, 40)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignCenter)

        # ── 상단 중단 버튼 ───────────────────────────────────────────────
        top_lay = QHBoxLayout()
        self._btn_cancel = QPushButton("중단하기")
        self._btn_cancel.setFont(QFont("Sans Serif", _fs(28)))
        self._btn_cancel.setFixedHeight(_fs(68))
        self._btn_cancel.setFixedWidth(_fs(200))
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                background: white;
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: 12px;
            }
            QPushButton:pressed { background: #f0f0f0; }
        """)
        self._btn_cancel.clicked.connect(self._on_auth_failure)
        top_lay.addWidget(self._btn_cancel)
        top_lay.addStretch()
        root.addLayout(top_lay)

        root.addStretch(1)

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

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setFixedWidth(520)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 4px;
                background: #bfdbfe;
            }}
            QProgressBar::chunk {{
                background-color: {_BLUE};
                border-radius: 4px;
            }}
        """)
        _prog_row = QHBoxLayout()
        _prog_row.addStretch()
        _prog_row.addWidget(self._progress_bar)
        _prog_row.addStretch()
        root.addLayout(_prog_row)
        root.addSpacing(16)

        self._title_lbl = QLabel("지문을 인증하는 중...")
        self._title_lbl.setFont(QFont("Sans Serif", _fs(52), QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._title_lbl)

        root.addSpacing(8)

        self._sub_lbl = QLabel("센서에 손가락을 올려주세요")
        self._sub_lbl.setFont(QFont("Sans Serif", _fs(36)))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setWordWrap(True)
        self._sub_lbl.setStyleSheet(f"color: {_BLUE};")
        root.addWidget(self._sub_lbl)

        root.addSpacing(8)

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(QFont("Sans Serif", _fs(38), QFont.Bold))
        self._pct_lbl.setAlignment(Qt.AlignCenter)
        self._pct_lbl.setStyleSheet(f"color: {_DARK};")
        root.addWidget(self._pct_lbl)

        root.addSpacing(24)

        # ── 재시도 버튼 영역 (실패 시에만 표시) ──────────────────────────
        self._retry_widget = QWidget()
        retry_row = QHBoxLayout(self._retry_widget)
        retry_row.setContentsMargins(0, 0, 0, 0)
        retry_row.setSpacing(24)

        self._btn_retry = QPushButton("다시 시도")
        self._btn_retry.setFont(QFont("Sans Serif", _fs(34), QFont.Bold))
        self._btn_retry.setFixedHeight(_fs(100))
        self._btn_retry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_retry.setStyleSheet(f"""
            QPushButton {{
                background-color: {_BLUE};
                color: white;
                border-radius: 18px;
                border: none;
            }}
            QPushButton:pressed {{ background-color: #2563eb; }}
        """)
        self._btn_retry.clicked.connect(self._on_retry)

        self._btn_give_up = QPushButton("취소")
        self._btn_give_up.setFont(QFont("Sans Serif", _fs(34), QFont.Bold))
        self._btn_give_up.setFixedHeight(_fs(100))
        self._btn_give_up.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_give_up.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {_RED};
                border-radius: 18px;
                border: 2px solid {_RED};
            }}
            QPushButton:pressed {{ background-color: #fef2f2; }}
        """)
        self._btn_give_up.clicked.connect(self._on_auth_failure)

        retry_row.addWidget(self._btn_retry)
        retry_row.addWidget(self._btn_give_up)

        self._retry_widget.hide()
        root.addWidget(self._retry_widget)

        # ── 전체 재시도 확인 영역 (얼굴 + 지문 모두 실패 시) ─────────────
        self._full_retry_widget = QWidget()
        full_retry_lay = QVBoxLayout(self._full_retry_widget)
        full_retry_lay.setContentsMargins(0, 0, 0, 0)
        full_retry_lay.setSpacing(16)
        full_retry_lay.setAlignment(Qt.AlignCenter)

        self._full_retry_title_lbl = QLabel("다시 시도하시겠습니까?")
        self._full_retry_title_lbl.setFont(QFont("Sans Serif", _fs(44), QFont.Bold))
        self._full_retry_title_lbl.setAlignment(Qt.AlignCenter)
        self._full_retry_title_lbl.setStyleSheet(f"color: {_DARK};")
        full_retry_lay.addWidget(self._full_retry_title_lbl)

        self._full_retry_sub_lbl = QLabel("얼굴 인증부터 다시 시작합니다")
        self._full_retry_sub_lbl.setFont(QFont("Sans Serif", _fs(32)))
        self._full_retry_sub_lbl.setAlignment(Qt.AlignCenter)
        self._full_retry_sub_lbl.setWordWrap(True)
        self._full_retry_sub_lbl.setStyleSheet("color: #6b7280;")
        full_retry_lay.addWidget(self._full_retry_sub_lbl)

        full_retry_btn_row = QHBoxLayout()
        full_retry_btn_row.setSpacing(24)

        self._btn_full_retry_yes = QPushButton("예, 처음부터")
        self._btn_full_retry_yes.setFont(QFont("Sans Serif", _fs(34), QFont.Bold))
        self._btn_full_retry_yes.setFixedHeight(_fs(100))
        self._btn_full_retry_yes.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_full_retry_yes.setStyleSheet(f"""
            QPushButton {{
                background-color: {_BLUE};
                color: white;
                border-radius: 18px;
                border: none;
            }}
            QPushButton:pressed {{ background-color: #2563eb; }}
        """)
        self._btn_full_retry_yes.clicked.connect(self._on_full_retry)

        self._btn_full_retry_no = QPushButton("아니오")
        self._btn_full_retry_no.setFont(QFont("Sans Serif", _fs(34), QFont.Bold))
        self._btn_full_retry_no.setFixedHeight(_fs(100))
        self._btn_full_retry_no.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._btn_full_retry_no.setStyleSheet(f"""
            QPushButton {{
                background-color: white;
                color: {_RED};
                border-radius: 18px;
                border: 2px solid {_RED};
            }}
            QPushButton:pressed {{ background-color: #fef2f2; }}
        """)
        self._btn_full_retry_no.clicked.connect(self._on_auth_failure_final)

        full_retry_btn_row.addWidget(self._btn_full_retry_yes)
        full_retry_btn_row.addWidget(self._btn_full_retry_no)
        full_retry_lay.addLayout(full_retry_btn_row)

        self._full_retry_widget.hide()
        root.addWidget(self._full_retry_widget)

        root.addStretch(2)

    # ── 생명주기 ─────────────────────────────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._retry_count = 0
        self._reset()
        self._start_auth()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_timers()

    # ── 내부 메서드 ──────────────────────────────────────────────────────────

    def _reset(self):
        self._progress_bar.setValue(0)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(0)
        self._pct_lbl.setText("0%")
        self._title_lbl.setText("센서에 손가락을 올려주세요")
        self._sub_lbl.setText(f"남은 시도 {_MAX_RETRIES - self._retry_count}회")
        self._sub_lbl.setStyleSheet(f"color: {_BLUE};")
        self._retry_widget.hide()
        self._full_retry_widget.hide()

    def _start_auth(self):
        self._stop_thread()

        from ui.threads.fingerprint_thread import FingerprintSearchThread
        self._thread = FingerprintSearchThread(parent=self)
        self._thread.found.connect(self._on_found)
        self._thread.not_found.connect(self._on_not_found)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)
        self._timeout_timer.start(_AUTH_TIMEOUT_MS)

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(2000)
        self._thread = None

    def _stop_timers(self):
        if self._timeout_timer and self._timeout_timer.isActive():
            self._timeout_timer.stop()
        self._stop_thread()

    def _show_retry_ui(self, msg: str):
        """실패 메시지 표시 + 재시도/취소 버튼 노출."""
        self._title_lbl.setText(msg)
        remaining = _MAX_RETRIES - self._retry_count
        if remaining > 0:
            self._sub_lbl.setText(f"남은 시도 {remaining}회")
            self._sub_lbl.setStyleSheet(f"color: {_RED};")
            self._btn_retry.show()
        else:
            self._sub_lbl.setText("최대 시도 횟수를 초과했습니다")
            self._sub_lbl.setStyleSheet(f"color: {_RED};")
            self._btn_retry.hide()
        self._retry_widget.show()

    # ── 시그널 핸들러 ─────────────────────────────────────────────────────────

    def _on_found(self, position: int, score: int):
        self._stop_timers()
        self._title_lbl.setText("인증 완료!")
        self._progress_bar.setValue(100)
        if hasattr(self._fp_widget, "set_progress"):
            self._fp_widget.set_progress(100)
        self._pct_lbl.setText("100%")
        self._retry_widget.hide()
        QTimer.singleShot(400, self._on_auth_success)

    def _on_not_found(self):
        self._stop_timers()
        self._retry_count += 1
        if self._retry_count >= _MAX_RETRIES:
            print(f"[FP_AUTH] Max retries ({_MAX_RETRIES}) reached. Showing final failure UI.")
            self._on_auth_failure() # 3회 실패 시 자동으로 전체 재시도 확인 화면으로
        else:
            print(f"[FP_AUTH] Not found. Retry {self._retry_count}/{_MAX_RETRIES}")
            self._title_lbl.setText("지문이 일치하지 않습니다")
            self._sub_lbl.setText(f"다시 센서에 손가락을 올려주세요 ({self._retry_count}/{_MAX_RETRIES})")
            QTimer.singleShot(1500, self._on_retry)

    def _on_failed(self, msg: str):
        self._stop_timers()
        self._retry_count += 1
        if self._retry_count >= _MAX_RETRIES:
            print(f"[FP_AUTH] Error: {msg}. Max retries reached.")
            self._on_auth_failure()
        else:
            print(f"[FP_AUTH] Error: {msg}. Retry {self._retry_count}/{_MAX_RETRIES}")
            self._title_lbl.setText("인증 중 오류 발생")
            QTimer.singleShot(1500, self._on_retry)

    def _on_timeout(self):
        self._stop_thread()
        self._retry_count += 1
        if self._retry_count >= _MAX_RETRIES:
            print("[FP_AUTH] Timeout. Max retries reached.")
            self._on_auth_failure()
        else:
            print(f"[FP_AUTH] Timeout. Retry {self._retry_count}/{_MAX_RETRIES}")
            self._on_retry()

    def _on_retry(self):
        self._retry_widget.hide()
        self._reset()
        self._start_auth()

    # ── 화면 전환 ─────────────────────────────────────────────────────────────

    def _on_auth_success(self):
        if not self._app:
            return
        if self._app.current_session.get("fp_test_mode"):
            self._app.current_session["fp_test_mode"] = False
            self._app.show_screen("home")
            return
        result = self._app.screens["auth_result"]
        result.set_result(success=True, fingerprint=True)
        self._app.show_screen("auth_result")

    def _on_auth_failure(self):
        """취소/실패 → 전체 재시도 확인 다이얼로그 표시."""
        self._stop_timers()
        self._retry_widget.hide()
        self._title_lbl.setText("인증에 실패했습니다")
        self._sub_lbl.setText("얼굴 인증부터 다시 시도할 수 있습니다")
        self._sub_lbl.setStyleSheet(f"color: {_RED};")
        self._full_retry_widget.show()

    def _on_full_retry(self):
        """처음부터 (얼굴 인증 화면으로 이동) 재시도."""
        self._full_retry_widget.hide()
        if self._app:
            if self._app.current_session.get("fp_test_mode"):
                self._app.current_session["fp_test_mode"] = False
                self._app.show_screen("home")
                return
            self._app.show_screen("camera_view")

    def _on_auth_failure_final(self):
        """최종 포기 → auth_result 실패 화면으로 이동."""
        self._full_retry_widget.hide()
        if not self._app:
            return
        if self._app.current_session.get("fp_test_mode"):
            self._app.current_session["fp_test_mode"] = False
            self._app.show_screen("home")
            return
        result = self._app.screens["auth_result"]
        result.set_result(success=False)
        self._app.show_screen("auth_result")
