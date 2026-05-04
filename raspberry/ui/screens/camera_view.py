import json
import os

import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter
from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.face_thread import AUTH_TIMEOUT_SEC, FaceThread, MODE_AUTH, MODE_REGISTER

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)


class _EmbeddingSaveWorker(QThread):
    # ... (기존과 동일하므로 생략하지 않고 전체 구조에 맞게 유지)
    done = pyqtSignal(bool)
    def __init__(self, face_imgs: list, parent=None):
        super().__init__(parent)
        self._face_imgs = face_imgs
    def run(self):
        try:
            from face_recognition.embedding import get_embedding
            embeddings = []
            for img in self._face_imgs:
                try: embeddings.append(get_embedding(img))
                except Exception: pass
            if not embeddings:
                self.done.emit(False)
                return
            mean_emb = np.mean(np.array(embeddings), axis=0).tolist()
            try:
                with open(_DB_PATH, "r", encoding="utf-8") as f: db = json.load(f)
            except Exception: db = {}
            db["_latest"] = mean_emb
            with open(_DB_PATH, "w", encoding="utf-8") as f: json.dump(db, f, indent=2)
            from api.client import upload_face_embedding
            ok = upload_face_embedding(mean_emb)
            self.done.emit(ok)
        except Exception: self.done.emit(False)


class _AuthWorker(QThread):
    """수집된 프레임들로 백그라운드 추론 실행 (다수결 투표 방식)."""
    success = pyqtSignal(str, float)
    failed  = pyqtSignal()

    def __init__(self, face_imgs: list, parent=None):
        super().__init__(parent)
        self._face_imgs = face_imgs

    def run(self):
        if not self._face_imgs:
            self.failed.emit()
            return
            
        from auth.authenticate import authenticate
        
        results = {}  # {user_name: [scores]}
        total_count = len(self._face_imgs)
        
        print(f"[AUTH_WORKER] Analyzing {total_count} frames (Strict Mode)...")

        for i, img in enumerate(self._face_imgs):
            user, score = authenticate(img)
            if user:
                if user not in results:
                    results[user] = []
                results[user].append(score)
        
        if not results:
            print("[AUTH_WORKER] Access Denied: No matching user found.")
            self.failed.emit()
            return

        # 다수결 및 보안 검증
        best_user = None
        max_votes = 0
        highest_avg = 0.0

        for user, scores in results.items():
            votes = len(scores)
            avg_score = sum(scores) / votes
            match_ratio = votes / total_count
            
            print(f"  - Candidate: {user} | Ratio: {match_ratio*100:.1f}% ({votes}/{total_count}) | Avg: {avg_score:.4f}")
            
            if votes > max_votes:
                max_votes = votes
                best_user = user
                highest_avg = avg_score
            elif votes == max_votes and avg_score > highest_avg:
                best_user = user
                highest_avg = avg_score

        # 보안 강화: 매칭 비율이 60% 이상이어야만 승인 (FAR 감소 핵심)
        STRICT_RATIO_THRESHOLD = 0.6
        final_ratio = max_votes / total_count

        if final_ratio >= STRICT_RATIO_THRESHOLD:
            print(f"[AUTH_WORKER] SUCCESS: {best_user} verified with {final_ratio*100:.1f}% confidence.")
            self.success.emit(best_user, float(highest_avg))
        else:
            print(f"[AUTH_WORKER] FAILED: Consistency too low ({final_ratio*100:.1f}%). Requires {STRICT_RATIO_THRESHOLD*100:.1f}%.")
            self.failed.emit()


_THEMES = {
    # ... (기존과 동일)
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
    # ... (기존과 동일)
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
        self._auth_worker     = None
        self._countdown_timer = None
        self._remaining       = 0
        self._frame_count     = 0
        self._auth_started    = False
        self._build_ui()

    def set_mode(self, mode: str, **kwargs):
        self._mode = mode
        self._apply_theme()

    def _build_ui(self):
        self._camera_card = CameraCardWidget(parent=self)
        self._gradient    = _GradientOverlay(parent=self)

        self._btn_cancel = QPushButton("중단", parent=self)
        self._btn_cancel.setFont(QFont("Sans Serif", 20, QFont.Bold))
        self._btn_cancel.setStyleSheet("background: rgba(255, 255, 255, 180); color: #374151; border-radius: 12px;")
        self._btn_cancel.clicked.connect(self._on_cancel)

        self._title_lbl = QLabel(parent=self)
        self._title_lbl.setFont(QFont("Sans Serif", 42, QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)

        self._sub_lbl = QLabel(parent=self)
        self._sub_lbl.setFont(QFont("Sans Serif", 34))
        self._sub_lbl.setAlignment(Qt.AlignCenter)

        # 오버레이들
        self._loading_lbl = QLabel("카메라 준비 중...", parent=self)
        self._loading_lbl.setFont(QFont("Sans Serif", 36, QFont.Bold))
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet("color: white; background: rgba(0,0,0,160); border-radius: 12px; padding: 12px 24px;")
        self._loading_lbl.hide()

        self._processing_overlay = QWidget(parent=self)
        self._processing_overlay.setStyleSheet("background-color: #1e293b;")
        self._processing_overlay.hide()
        
        proc_lay = QVBoxLayout(self._processing_overlay)
        self._proc_msg = QLabel("사용자 확인 중입니다...\n잠시만 기다려 주세요", self._processing_overlay)
        self._proc_msg.setFont(QFont("Sans Serif", 40, QFont.Bold))
        self._proc_msg.setAlignment(Qt.AlignCenter)
        self._proc_msg.setStyleSheet("color: white;")
        proc_lay.addWidget(self._proc_msg)

        self._apply_theme()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._camera_card.setGeometry(0, 0, w, h)
        self._btn_cancel.setGeometry(w - 140, 25, 120, 60)
        overlay_h = int(h * 0.32)
        self._gradient.setGeometry(0, h - overlay_h, w, overlay_h)
        self._title_lbl.setGeometry(0, h - int(h * 0.22), w, 64)
        self._sub_lbl.setGeometry(0, h - int(h * 0.12), w, 52)
        self._loading_lbl.setGeometry((w-400)//2, (h-100)//2, 400, 100)
        self._processing_overlay.setGeometry(0, 0, w, h)

    def _apply_theme(self):
        t = _THEMES.get(self._mode, _THEMES[MODE_AUTH])
        self._camera_card.set_dash_color(t["dash"])
        self._title_lbl.setText(t["title"])
        self._title_lbl.setStyleSheet(f"color: {t['title_color']}; background: transparent;")
        self._sub_lbl.setText(t["sub"])
        self._sub_lbl.setStyleSheet(f"color: {t['sub_color']}; background: transparent;")

    def showEvent(self, event):
        super().showEvent(event)
        self._processing_overlay.hide()
        self._apply_theme()
        self._start_thread()

    def hideEvent(self, event):
        super().hideEvent(event)
        self._stop_thread()

    def _start_thread(self):
        self._stop_thread()
        self._frame_count  = 0
        self._auth_started = False
        self._loading_lbl.show()
        self._thread = FaceThread(mode=self._mode)
        self._thread.frame_ready.connect(self._on_frame_ready)
        self._thread.capture_done.connect(self._on_capture_done)

        if self._mode == MODE_AUTH:
            self._thread.auth_failed.connect(self._on_auth_failed)
        else:
            self._thread.capture_progress.connect(self._on_progress)
            self._thread.phase_changed.connect(self._on_phase_changed)

        self._thread.start()

    def _stop_thread(self):
        if self._countdown_timer: self._countdown_timer.stop()
        self._countdown_timer = None
        if self._thread:
            self._thread.stop()
            self._thread.wait(2000)
        self._thread = None

    def _on_frame_ready(self, frame):
        self._camera_card.update_frame(frame)
        self._frame_count += 1
        if not self._auth_started and self._frame_count >= _CAMERA_READY_FRAMES:
            self._auth_started = True
            self._loading_lbl.hide()
            if self._mode == MODE_AUTH:
                self._begin_auth_countdown()

    def _begin_auth_countdown(self):
        self._remaining = AUTH_TIMEOUT_SEC
        self._update_auth_status()
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._tick_countdown)
        self._countdown_timer.start(1000)

    def _tick_countdown(self):
        self._remaining -= 1
        self._update_auth_status()
        if self._remaining <= 0: self._countdown_timer.stop()

    def _update_auth_status(self):
        self._sub_lbl.setText(f"정면을 바라봐 주세요  ({self._remaining}초)")

    def _on_cancel(self):
        self._stop_thread()
        if self._app: self._app.show_screen("home")

    def _on_capture_done(self, face_imgs: list):
        """[중요] 캡처 완료 시 모드에 따라 처리."""
        self._stop_thread()
        
        if self._mode == MODE_REGISTER:
            self._sub_lbl.setText("저장 중...")
            self._save_worker = _EmbeddingSaveWorker(face_imgs, parent=self)
            self._save_worker.done.connect(self._on_save_done)
            self._save_worker.start()
        else:
            # 인증 모드: 카메라 숨기고 추론 시작
            self._processing_overlay.show()
            self._auth_worker = _AuthWorker(face_imgs, parent=self)
            self._auth_worker.success.connect(self._on_auth_success)
            self._auth_worker.failed.connect(self._on_auth_failed)
            self._auth_worker.start()

    def _on_auth_success(self, user: str, score: float):
        if self._app:
            self._app.current_session["face_verified"] = True
            self._app.current_session["similarity_score"] = score
        result = self._app.screens["auth_result"]
        result.set_result(success=True, user=user)
        self._app.show_screen("auth_result")

    def _on_auth_failed(self):
        self._stop_thread()
        if self._app: self._app.show_screen("fingerprint_auth")

    def _on_progress(self, count: int):
        phase_in_count = ((count - 1) % 4) + 1
        self._sub_lbl.setText(f"촬영 중...  {phase_in_count} / 4")

    def _on_phase_changed(self, phase_idx: int, direction: str):
        if phase_idx < 0:
            # 카운트다운 중 (-2, -1 순서로 옴)
            countdown = abs(phase_idx)
            self._sub_lbl.setText(f"다음 방향 준비: {direction}  ({countdown}초)")
            self._sub_lbl.setStyleSheet("color: #fbbf24; background: transparent;")
        else:
            self._sub_lbl.setText(f"{direction}을(를) 바라봐 주세요")
            self._sub_lbl.setStyleSheet("color: #93c5fd; background: transparent;")

    def _on_save_done(self, ok: bool):
        if self._app: self._app.show_screen("fingerprint_register")
