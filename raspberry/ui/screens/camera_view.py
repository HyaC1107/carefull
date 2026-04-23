import json
import os

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.face_thread import FaceThread, MODE_AUTH, MODE_REGISTER

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)

# 모드별 테마
_THEMES = {
    MODE_REGISTER: {
        "bg":         "#ede8ff",
        "dash":       "#7c3aed",
        "title":      "얼굴을 맞춰주세요",
        "sub":        "자동으로 촬영합니다",
        "title_color": "#1e1b4b",
        "sub_color":   "#7c3aed",
    },
    MODE_AUTH: {
        "bg":         "#e4ecff",
        "dash":       "#3b82f6",
        "title":      "얼굴을 화면 중앙에 맞춰주세요",
        "sub":        "카메라를 바라봐 주세요",
        "title_color": "#1e3a8a",
        "sub_color":   "#3b82f6",
    },
}


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
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 24)
        root.setSpacing(0)

        self._camera_card = CameraCardWidget()
        self._camera_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._camera_card, stretch=3)

        root.addSpacing(18)

        self._title_lbl = QLabel()
        self._title_lbl.setFont(QFont("Sans Serif", 20, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._title_lbl)

        root.addSpacing(6)

        self._sub_lbl = QLabel()
        self._sub_lbl.setFont(QFont("Sans Serif", 15))
        self._sub_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._sub_lbl)

        root.addStretch(1)

        self._apply_theme()

    def _apply_theme(self):
        t = _THEMES.get(self._mode, _THEMES[MODE_AUTH])
        self.setStyleSheet(f"background-color: {t['bg']};")
        self._camera_card.set_dash_color(t["dash"])
        self._title_lbl.setText(t["title"])
        self._title_lbl.setStyleSheet(f"color: {t['title_color']};")
        self._sub_lbl.setText(t["sub"])
        self._sub_lbl.setStyleSheet(f"color: {t['sub_color']};")

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

    # ─────────────────────────────── 콜백: auth ───────────────────────────────

    def _on_auth_success(self, user: str):
        self._stop_thread()
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
        except Exception as e:
            print(f"[REGISTER ERROR] {e}")
