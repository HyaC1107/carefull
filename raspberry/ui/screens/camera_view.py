import json
import os

import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt5.QtWidgets import QLabel, QPushButton, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.face_thread import AUTH_TIMEOUT_SEC, FaceThread, MODE_AUTH, MODE_REGISTER

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)


class _EmbeddingSaveWorker(QThread):
    """TFLite 추론 + 서버 업로드를 백그라운드에서 처리."""
    done = pyqtSignal(bool)   # True = 업로드 성공

    def __init__(self, face_imgs: list, parent=None):
        super().__init__(parent)
        self._face_imgs = face_imgs

    def run(self):
        try:
            from face_recognition.embedding import get_embedding
            embeddings = []
            for img in self._face_imgs:
                try:
                    embeddings.append(get_embedding(img))
                except Exception:
                    pass
            if not embeddings:
                self.done.emit(False)
                return

            mean_emb = np.mean(np.array(embeddings), axis=0).tolist()

            # 로컬 캐시 저장
            try:
                with open(_DB_PATH, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                db = {}
            db["_latest"] = mean_emb
            with open(_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)

            # 서버 업로드
            from api.client import upload_face_embedding
            ok = upload_face_embedding(mean_emb)
            if not ok:
                print("[REGISTER] face embedding upload failed")
            self.done.emit(ok)

        except Exception as e:
            print(f"[REGISTER ERROR] {e}")
            self.done.emit(False)

_THEMES = {
    MODE_REGISTER: {
        "dash":        "#7c3aed",
        "title":       "얼굴을 맞춰주세요",
        "sub":         "자동으로 촬영합니다",
        "title_color": "#ffffff",
        "sub_color":   "#c4b5fd",
    },
    MODE_AUTH: {
        "dash":        "#3b82f6",
        "title":       "얼굴을 화면 중앙에 맞춰주세요",
        "sub":         "카메라를 바라봐 주세요",
        "title_color": "#ffffff",
        "sub_color":   "#93c5fd",
    },
}

# 카메라가 완전히 준비될 때까지 대기 (프레임 수 기준)
_CAMERA_READY_FRAMES = 5


class _GradientOverlay(QWidget):
    """하단 텍스트 가독성을 위한 반투명 그라데이션."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(0, 0, 0, 180))
        p.fillRect(self.rect(), grad)


class CameraViewScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app             = parent
        self._mode            = MODE_AUTH
        self._thread          = None
        self._save_worker     = None
        self._countdown_timer = None
        self._remaining       = 0
        self._frame_count     = 0   # 카메라 준비 판단용
        self._auth_started    = False
        self._build_ui()

    def set_mode(self, mode: str, **kwargs):
        self._mode = mode
        self._apply_theme()

    # ─────────────────────────────── UI ──────────────────────────────────────

    def _build_ui(self):
        self._camera_card = CameraCardWidget(parent=self)
        self._gradient    = _GradientOverlay(parent=self)

        # 중단 버튼 추가
        self._btn_cancel = QPushButton("중단", parent=self)
        self._btn_cancel.setFont(QFont("Sans Serif", 20, QFont.Bold))
        self._btn_cancel.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 180);
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: 12px;
            }
            QPushButton:pressed { background: white; }
        """)
        self._btn_cancel.clicked.connect(self._on_cancel)

        self._title_lbl = QLabel(parent=self)
        self._title_lbl.setFont(QFont("Sans Serif", 42, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._sub_lbl = QLabel(parent=self)
        self._sub_lbl.setFont(QFont("Sans Serif", 34))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        # 카메라 준비 중 오버레이
        self._loading_lbl = QLabel("카메라 준비 중...", parent=self)
        self._loading_lbl.setFont(QFont("Sans Serif", 36, QFont.Bold))
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet(
            "color: white; background: rgba(0,0,0,160); border-radius: 12px; padding: 12px 24px;"
        )
        self._loading_lbl.adjustSize()

        self._apply_theme()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        self._camera_card.setGeometry(0, 0, w, h)

        # 우측 상단 중단 버튼 배치
        self._btn_cancel.setGeometry(w - 140, 25, 120, 60)

        overlay_h = int(h * 0.32)
        self._gradient.setGeometry(0, h - overlay_h, w, overlay_h)

        self._title_lbl.setGeometry(0, h - int(h * 0.22), w, 64)
        self._sub_lbl.setGeometry(0, h - int(h * 0.12), w, 52)

        # 로딩 레이블 중앙
        lw, lh = self._loading_lbl.sizeHint().width() + 64, 72
        self._loading_lbl.setGeometry((w - lw) // 2, (h - lh) // 2, lw, lh)

    def _apply_theme(self):
        t = _THEMES.get(self._mode, _THEMES[MODE_AUTH])
        self._camera_card.set_dash_color(t["dash"])
        self._title_lbl.setText(t["title"])
        self._title_lbl.setStyleSheet(f"color: {t['title_color']}; background: transparent;")
        self._sub_lbl.setText(t["sub"])
        self._sub_lbl.setStyleSheet(f"color: {t['sub_color']}; background: transparent;")

    # ─────────────────────────────── 생명주기 ────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_theme()
        self._start_thread()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_thread()

    # ─────────────────────────────── 스레드 ──────────────────────────────────

    def _start_thread(self):
        self._stop_thread()
        self._frame_count  = 0
        self._auth_started = False

        self._loading_lbl.show()
        self._loading_lbl.raise_()

        self._thread = FaceThread(mode=self._mode)
        self._thread.frame_ready.connect(self._on_frame_ready)

        if self._mode == MODE_AUTH:
            self._thread.auth_success.connect(self._on_auth_success)
            self._thread.auth_failed.connect(self._on_auth_failed)
        else:
            self._thread.capture_progress.connect(self._on_progress)
            self._thread.capture_done.connect(self._on_capture_done)

        self._thread.start()

    def _stop_thread(self):
        if self._countdown_timer and self._countdown_timer.isActive():
            self._countdown_timer.stop()
        self._countdown_timer = None
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(3000)
        self._thread = None

    # ─────────────────────────────── 프레임 수신 ─────────────────────────────

    def _on_frame_ready(self, frame):
        self._camera_card.update_frame(frame)
        self._frame_count += 1

        # 카메라가 준비됐다고 판단되면 인증 타이머 시작
        if not self._auth_started and self._frame_count >= _CAMERA_READY_FRAMES:
            self._auth_started = True
            self._loading_lbl.hide()
            if self._mode == MODE_AUTH:
                self._begin_auth_countdown()

    def _begin_auth_countdown(self):
        """카메라 준비 완료 후 인증 카운트다운 시작."""
        self._remaining = AUTH_TIMEOUT_SEC
        self._update_auth_status()

        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)
        self._countdown_timer.start(1000)

    def _tick_countdown(self):
        self._remaining -= 1
        self._update_auth_status()
        if self._remaining <= 0:
            self._countdown_timer.stop()

    def _update_auth_status(self):
        self._sub_lbl.setText(f"정면을 바라봐 주세요  ({self._remaining}초)")

    # ─────────────────────────────── 콜백: auth ──────────────────────────────

    def _on_cancel(self):
        self._stop_thread()
        if self._app:
            self._app.show_screen("home")

    def _on_auth_success(self, user: str, score: float):
        self._stop_thread()
        if self._app:
            self._app.current_session["face_verified"]    = True
            self._app.current_session["similarity_score"] = score
        result = self._app.screens["auth_result"]
        result.set_result(success=True, user=user)
        self._app.show_screen("auth_result")

    def _on_auth_failed(self):
        self._stop_thread()
        if self._app:
            self._app.show_screen("fingerprint_auth")

    # ─────────────────────────────── 콜백: register ──────────────────────────

    def _on_progress(self, count: int):
        if count <= 5:
            guide = "정면을 바라봐 주세요"
        elif count <= 10:
            guide = "고개를 왼쪽으로 살짝 돌려주세요"
        elif count <= 15:
            guide = "고개를 오른쪽으로 살짝 돌려주세요"
        else:
            guide = "고개를 위아래로 천천히 움직여주세요"
            
        self._sub_lbl.setText(f"{guide}  ({count} / 20)")

    def _on_capture_done(self, face_imgs: list):
        self._sub_lbl.setText("저장 중...")
        self._stop_thread()
        # 백그라운드 워커에서 TFLite 추론 + 서버 업로드 (UI 블로킹 방지)
        self._save_worker = _EmbeddingSaveWorker(face_imgs, parent=self)
        self._save_worker.done.connect(self._on_save_done)
        self._save_worker.start()

    def _on_save_done(self, ok: bool):
        if not ok:
            print("[REGISTER] embedding save failed — proceeding to fingerprint step anyway")
        if self._app:
            self._app.show_screen("fingerprint_register")
