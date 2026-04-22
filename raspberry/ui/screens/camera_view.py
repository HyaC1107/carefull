import json
import os

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ui.widgets.camera_widget import CameraWidget
from ui.threads.face_thread import FaceThread, MODE_AUTH, MODE_REGISTER

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)


class CameraViewScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._mode = MODE_AUTH
        self._user_name = None
        self._thread = None
        self._build_ui()

    def set_mode(self, mode: str, user_name: str = None):
        self._mode = mode
        self._user_name = user_name

    # ──────────────────────────────── UI ─────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._camera_widget = CameraWidget()
        self._camera_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._camera_widget, stretch=1)

        # 하단 패널
        bottom = QWidget()
        bottom.setFixedHeight(180)
        bottom.setStyleSheet("background-color: #1a1a2e;")
        b_lay = QVBoxLayout(bottom)
        b_lay.setContentsMargins(24, 14, 24, 20)
        b_lay.setSpacing(12)

        self._status_lbl = QLabel("얼굴을 카메라에 맞춰주세요")
        self._status_lbl.setFont(QFont("Sans Serif", 20))
        self._status_lbl.setStyleSheet("color: white;")
        self._status_lbl.setAlignment(Qt.AlignCenter)

        cancel_btn = QPushButton("취소")
        cancel_btn.setMinimumHeight(64)
        cancel_btn.setFont(QFont("Sans Serif", 20))
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 14px;
            }
            QPushButton:pressed { background-color: #5a6268; }
        """)
        cancel_btn.clicked.connect(self._cancel)

        b_lay.addWidget(self._status_lbl)
        b_lay.addWidget(cancel_btn)
        root.addWidget(bottom)

    # ──────────────────────────────── 생명주기 ────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        self._start_thread()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_thread()

    # ──────────────────────────────── 스레드 ─────────────────────────────────

    def _start_thread(self):
        self._stop_thread()
        self._thread = FaceThread(mode=self._mode)
        self._thread.frame_ready.connect(self._camera_widget.update_frame)

        if self._mode == MODE_AUTH:
            self._status_lbl.setText("얼굴을 카메라에 맞춰주세요")
            self._thread.auth_success.connect(self._on_auth_success)
            self._thread.auth_failed.connect(self._on_auth_failed)
        else:
            self._status_lbl.setText(f"정면을 바라봐 주세요  (0 / 20)")
            self._thread.capture_progress.connect(self._on_progress)
            self._thread.capture_done.connect(self._on_capture_done)

        self._thread.start()

    def _stop_thread(self):
        if self._thread and self._thread.isRunning():
            self._thread.stop()
            self._thread.wait(3000)
        self._thread = None

    # ──────────────────────────────── 콜백: auth ──────────────────────────────

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

    # ──────────────────────────────── 콜백: register ─────────────────────────

    def _on_progress(self, count: int):
        self._status_lbl.setText(f"촬영 중...  ({count} / 20)")

    def _on_capture_done(self, face_imgs: list):
        self._status_lbl.setText("등록 저장 중...")
        self._stop_thread()
        self._save_mean_embedding(face_imgs)
        self._app.show_screen("home")

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

            db[self._user_name] = mean_emb

            with open(_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[REGISTER ERROR] {e}")

    # ──────────────────────────────── 취소 ───────────────────────────────────

    def _cancel(self):
        self._stop_thread()
        self._app.show_screen("home")
