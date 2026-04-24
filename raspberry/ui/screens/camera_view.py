import json
import os

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt5.QtWidgets import QLabel, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.face_thread import FaceThread, MODE_AUTH, MODE_REGISTER

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)

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
        self._app = parent
        self._mode = MODE_AUTH
        self._thread = None
        self._build_ui()

    def set_mode(self, mode: str, **kwargs):
        self._mode = mode
        self._apply_theme()

    # ─────────────────────────────── UI ──────────────────────────────────────

    def _build_ui(self):
        # 카메라 — 전체 화면
        self._camera_card = CameraCardWidget(parent=self)

        # 하단 그라데이션 오버레이
        self._gradient = _GradientOverlay(parent=self)

        # 텍스트 레이블 — 카메라 위에 오버레이
        self._title_lbl = QLabel(parent=self)
        self._title_lbl.setFont(QFont("Sans Serif", 20, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        self._title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._sub_lbl = QLabel(parent=self)
        self._sub_lbl.setFont(QFont("Sans Serif", 15))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        self._sub_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._apply_theme()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()

        self._camera_card.setGeometry(0, 0, w, h)

        overlay_h = 130
        self._gradient.setGeometry(0, h - overlay_h, w, overlay_h)

        self._title_lbl.setGeometry(0, h - 85, w, 38)
        self._sub_lbl.setGeometry(0, h - 44, w, 30)

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
        self._thread = FaceThread(mode=self._mode)
        self._thread.frame_ready.connect(self._camera_card.update_frame)

        if self._mode == MODE_AUTH:
            self._thread.auth_success.connect(self._on_auth_success)
            self._thread.auth_failed.connect(self._on_auth_failed)
        else:
            self._thread.capture_progress.connect(self._on_progress)
            self._thread.capture_done.connect(self._on_capture_done)

        self._thread.start()

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(3000)
        self._thread = None

    # ─────────────────────────────── 콜백: auth ──────────────────────────────

    def _on_auth_success(self, user: str, score: float):
        self._stop_thread()
        if self._app:
            self._app.current_session["face_verified"] = True
            self._app.current_session["similarity_score"] = score
        result = self._app.screens["auth_result"]
        result.set_result(success=True, user=user)
        self._app.show_screen("auth_result")

    def _on_auth_failed(self):
        self._stop_thread()
        result = self._app.screens["auth_result"]
        result.set_result(success=False)
        self._app.show_screen("auth_result")

    # ─────────────────────────────── 콜백: register ──────────────────────────

    def _on_progress(self, count: int):
        self._sub_lbl.setText(f"촬영 중...  ({count} / 20)")

    def _on_capture_done(self, face_imgs: list):
        self._sub_lbl.setText("저장 중...")
        self._stop_thread()
        self._save_mean_embedding(face_imgs)
        self._app.show_screen("fingerprint_register")

    def _save_mean_embedding(self, face_imgs: list):
        try:
            from face_recognition.embedding import get_embedding
            embeddings = []
            for img in face_imgs:
                try:
                    embeddings.append(get_embedding(img))
                except Exception:
                    pass
            if not embeddings:
                return
            mean_emb = np.mean(np.array(embeddings), axis=0).tolist()
            try:
                with open(_DB_PATH, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                db = {}
            db["_latest"] = mean_emb
            with open(_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)
            try:
                from api.client import upload_face_embedding
                upload_face_embedding(mean_emb)
            except Exception:
                pass
        except Exception as e:
            print(f"[REGISTER ERROR] {e}")
