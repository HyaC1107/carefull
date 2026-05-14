import json
import os

import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QLinearGradient, QPainter
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.widgets.camera_card_widget import CameraCardWidget
from ui.threads.face_thread import AUTH_TIMEOUT_SEC, FaceThread, MODE_AUTH, MODE_REGISTER
from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

def _play_voice(filename: str):
    try:
        from hardware.alarm import play_voice
        play_voice(filename)
    except Exception:
        pass


_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)


class _EmbeddingSaveWorker(QThread):
    done = pyqtSignal(bool)
    def __init__(self, face_imgs: list, parent=None):
        super().__init__(parent)
        self._face_imgs = face_imgs
    def run(self):
        try:
            from face_recognition.embedding import get_embedding
            # 1. 품질(이미지 크기) 순으로 정렬하여 상위 10장 선택
            # face_imgs는 [H, W, C] 형태의 ndarray 리스트
            self._face_imgs.sort(key=lambda img: img.shape[0] * img.shape[1], reverse=True)
            best_imgs = self._face_imgs[:10]
            
            embeddings = []
            for img in best_imgs:
                try: 
                    emb = get_embedding(img)
                    embeddings.append(emb.tolist())
                except Exception: pass
                
            if not embeddings:
                self.done.emit(False)
                return
            
            # 2. 평균 대신 리스트(Multi-Template)로 저장
            try:
                with open(_DB_PATH, "r", encoding="utf-8") as f: db = json.load(f)
            except Exception: db = {}
            
            # "_latest" 키에 벡터 리스트 저장
            db["_latest"] = embeddings
            
            with open(_DB_PATH, "w", encoding="utf-8") as f: 
                json.dump(db, f, indent=2)
                
            # 서버 업로드 (서버도 리스트를 받을 수 있도록 처리 - 여기서는 대표로 평균값 전송하거나 리스트 전송)
            from api.client import upload_face_embedding
            from auth.authenticate import invalidate_embedding_cache
            
            # 서버에는 호환성을 위해 상위 10개의 평균을 보냄
            mean_emb = np.mean(np.array(embeddings), axis=0).tolist()
            ok = upload_face_embedding(mean_emb)
            
            invalidate_embedding_cache()
            self.done.emit(True) # 로컬 저장 성공 시 True
        except Exception as e:
            print(f"[SAVE_WORKER] Error: {e}")
            self.done.emit(False)


class _AuthWorker(QThread):
    """수집된 프레임들로 백그라운드 추론 실행 (다수결 투표 방식)."""
    success = pyqtSignal(str, float)
    failed  = pyqtSignal()

    def __init__(self, face_imgs: list, parent=None):
        super().__init__(parent)
        self._face_imgs = face_imgs

    def run(self):
        import csv, datetime
        from config.settings import BASE_DIR

        if not self._face_imgs:
            self.failed.emit()
            return

        from auth.authenticate import authenticate

        results = {}  # {user_name: [scores]}
        total_count = len(self._face_imgs)
        frame_logs = []  # CSV 저장용
        session_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        print(f"[AUTH_WORKER] Analyzing {total_count} frames (Multi-Template Mode)...")

        for i, img in enumerate(self._face_imgs):
            user, score = authenticate(img)
            status = "MATCH" if user else "FAIL"
            print(f"[AUTH_FRAME] {i+1:02d}/{total_count} | Score: {score:.4f} ({status})")
            frame_logs.append((session_ts, i + 1, total_count, round(score, 4), status))

            if user:
                if user not in results:
                    results[user] = []
                results[user].append(score)

        if not results:
            print("[AUTH_WORKER] Access Denied: No matching user found.")
            _append_face_log(BASE_DIR, frame_logs, final_result="DENIED", match_ratio=0.0, avg_score=0.0)
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

        STRICT_RATIO_THRESHOLD = 0.50
        final_ratio = max_votes / total_count

        if final_ratio >= STRICT_RATIO_THRESHOLD:
            print(f"[AUTH_WORKER] SUCCESS: {best_user} verified with {final_ratio*100:.1f}% confidence.")
            _append_face_log(BASE_DIR, frame_logs, final_result="SUCCESS",
                             match_ratio=round(final_ratio, 4), avg_score=round(highest_avg, 4))
            self.success.emit(best_user, float(highest_avg))
        else:
            print(f"[AUTH_WORKER] FAILED: Consistency too low ({final_ratio*100:.1f}%). Requires {STRICT_RATIO_THRESHOLD*100:.1f}%.")
            _append_face_log(BASE_DIR, frame_logs, final_result="FAILED",
                             match_ratio=round(final_ratio, 4), avg_score=round(highest_avg, 4))
            self.failed.emit()


def _append_face_log(base_dir: str, frame_logs: list, final_result: str, match_ratio: float, avg_score: float):
    """얼굴 인증 결과를 CSV에 추가."""
    import csv, os
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "face_auth_log.csv")
    write_header = not os.path.exists(log_path)
    try:
        with open(log_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if write_header:
                w.writerow(["session_time", "frame_no", "total_frames",
                            "similarity_score", "frame_result",
                            "match_ratio", "avg_score", "final_result"])
            for row in frame_logs:
                w.writerow(list(row) + [match_ratio, avg_score, final_result])
    except Exception as e:
        print(f"[AUTH_LOG] 로그 저장 실패: {e}")


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
        self._app                  = parent
        self._mode                 = MODE_AUTH
        self._thread               = None
        self._save_worker          = None
        self._auth_worker          = None
        self._countdown_timer      = None
        self._fingerprint_timer    = None   # 취소 가능한 지문 전환 타이머
        self._auth_result_handled  = False  # success/failed 중복 처리 방지
        self._remaining            = 0
        self._frame_count          = 0
        self._auth_started         = False
        self._build_ui()

    def set_mode(self, mode: str, **kwargs):
        self._mode = mode
        self._apply_theme()

    def _build_ui(self):
        self._camera_card = CameraCardWidget(parent=self)
        self._gradient    = _GradientOverlay(parent=self)

        self._btn_cancel = QPushButton("중단", parent=self)
        self._btn_cancel.setFont(QFont("Sans Serif", _fs(26), QFont.Bold))
        self._btn_cancel.setStyleSheet("background: rgba(255, 255, 255, 180); color: #374151; border-radius: 12px;")
        self._btn_cancel.clicked.connect(self._on_cancel)

        self._title_lbl = QLabel(parent=self)
        self._title_lbl.setFont(QFont("Sans Serif", _fs(52), QFont.Bold))
        self._title_lbl.setAlignment(Qt.AlignCenter)

        self._sub_lbl = QLabel(parent=self)
        self._sub_lbl.setFont(QFont("Sans Serif", _fs(42)))
        self._sub_lbl.setAlignment(Qt.AlignCenter)

        # 오버레이들
        self._loading_lbl = QLabel("카메라 준비 중...", parent=self)
        self._loading_lbl.setFont(QFont("Sans Serif", _fs(44), QFont.Bold))
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet("color: white; background: rgba(0,0,0,160); border-radius: 12px; padding: 12px 24px;")
        self._loading_lbl.hide()

        self._processing_overlay = QWidget(parent=self)
        self._processing_overlay.setStyleSheet("background-color: #1e293b;")
        self._processing_overlay.hide()

        proc_lay = QVBoxLayout(self._processing_overlay)
        self._proc_msg = QLabel("사용자 확인 중입니다...\n잠시만 기다려 주세요", self._processing_overlay)
        self._proc_msg.setFont(QFont("Sans Serif", _fs(48), QFont.Bold))
        self._proc_msg.setAlignment(Qt.AlignCenter)
        self._proc_msg.setStyleSheet("color: white;")
        proc_lay.addWidget(self._proc_msg)

        # ── 업로드 실패 오버레이 (등록 모드, 서버 전송 실패 시) ──────────────
        self._upload_error_overlay = QWidget(parent=self)
        self._upload_error_overlay.setStyleSheet("background-color: #1e293b;")
        self._upload_error_overlay.hide()

        err_lay = QVBoxLayout(self._upload_error_overlay)
        err_lay.setAlignment(Qt.AlignCenter)
        err_lay.setSpacing(20)

        _err_title = QLabel("서버 저장에 실패했습니다", self._upload_error_overlay)
        _err_title.setFont(QFont("Sans Serif", 36, QFont.Bold))
        _err_title.setAlignment(Qt.AlignCenter)
        _err_title.setStyleSheet("color: white;")
        err_lay.addWidget(_err_title)

        _err_sub = QLabel("로컬 저장은 완료됐습니다\n다시 시도하거나 계속 진행할 수 있습니다",
                          self._upload_error_overlay)
        _err_sub.setFont(QFont("Sans Serif", 26))
        _err_sub.setAlignment(Qt.AlignCenter)
        _err_sub.setStyleSheet("color: #94a3b8;")
        err_lay.addWidget(_err_sub)

        err_btn_row = QHBoxLayout()
        err_btn_row.setSpacing(24)
        err_btn_row.setAlignment(Qt.AlignCenter)

        self._btn_upload_retry = QPushButton("다시 시도", self._upload_error_overlay)
        self._btn_upload_retry.setFont(QFont("Sans Serif", _fs(28), QFont.Bold))
        self._btn_upload_retry.setFixedHeight(_fs(90))
        self._btn_upload_retry.setFixedWidth(_fs(320))
        self._btn_upload_retry.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 16px;
                border: none;
            }
            QPushButton:pressed { background-color: #2563eb; }
        """)
        self._btn_upload_retry.clicked.connect(self._on_upload_retry)

        self._btn_upload_continue = QPushButton("계속 진행", self._upload_error_overlay)
        self._btn_upload_continue.setFont(QFont("Sans Serif", _fs(28), QFont.Bold))
        self._btn_upload_continue.setFixedHeight(_fs(90))
        self._btn_upload_continue.setFixedWidth(_fs(320))
        self._btn_upload_continue.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border-radius: 16px;
                border: 2px solid white;
            }
            QPushButton:pressed { background-color: rgba(255,255,255,30); }
        """)
        self._btn_upload_continue.clicked.connect(self._on_upload_continue)

        err_btn_row.addWidget(self._btn_upload_retry)
        err_btn_row.addWidget(self._btn_upload_continue)
        err_lay.addLayout(err_btn_row)

        self._apply_theme()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self._camera_card.setGeometry(0, 0, w, h)
        
        btn_w, btn_h = _fs(140), _fs(60)
        self._btn_cancel.setGeometry(w - btn_w - _fs(20), _fs(20), btn_w, btn_h)

        # 폰트 실측 높이 기반으로 label geometry 계산 (고정px 쓰면 잘림)
        title_h = QFontMetrics(self._title_lbl.font()).height() + _fs(16)
        sub_h   = QFontMetrics(self._sub_lbl.font()).height() + _fs(14)
        pad_bot = _fs(24)
        sub_y   = h - pad_bot - sub_h
        title_y = sub_y - _fs(12) - title_h

        gradient_top = max(0, title_y - _fs(24))
        self._gradient.setGeometry(0, gradient_top, w, h - gradient_top)
        self._title_lbl.setGeometry(0, title_y, w, title_h)
        self._sub_lbl.setGeometry(0, sub_y, w, sub_h)

        loading_fm = QFontMetrics(self._loading_lbl.font())
        loading_w  = loading_fm.horizontalAdvance(self._loading_lbl.text()) + _fs(56)
        loading_h  = loading_fm.height() + _fs(28)
        self._loading_lbl.setGeometry((w - loading_w) // 2, (h - loading_h) // 2, loading_w, loading_h)
        self._processing_overlay.setGeometry(0, 0, w, h)
        self._upload_error_overlay.setGeometry(0, 0, w, h)

    def _apply_theme(self):
        t = _THEMES.get(self._mode, _THEMES[MODE_AUTH])
        self._camera_card.set_dash_color(t["dash"])
        self._title_lbl.setText(t["title"])
        self._title_lbl.setStyleSheet(f"color: {t['title_color']}; background: transparent;")
        self._sub_lbl.setText(t["sub"])
        self._sub_lbl.setStyleSheet(f"color: {t['sub_color']}; background: transparent;")

    def showEvent(self, event):
        super().showEvent(event)
        self._auth_result_handled = False
        
        # [FIX] 오버레이 상태 초기화: 이전 실패 잔상이 남지 않도록 기본값으로 복원
        self._processing_overlay.setStyleSheet("background-color: #1e293b;")
        self._proc_msg.setText("사용자 확인 중입니다...\n잠시만 기다려 주세요")
        self._proc_msg.setStyleSheet("color: white;")
        
        self._processing_overlay.hide()
        self._upload_error_overlay.hide()
        self._last_face_imgs = []
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
            self._thread.auth_success.connect(self._on_auth_success)
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
                _play_voice("med_auth_face.mp3")
                self._begin_auth_countdown()
            elif self._mode == MODE_REGISTER:
                _play_voice("reg_face_guide.mp3")

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

    def _stop_auth_worker(self):
        """이전 AuthWorker 시그널 연결 해제 및 정리."""
        if self._auth_worker is not None:
            try:
                self._auth_worker.success.disconnect(self._on_auth_success)
                self._auth_worker.failed.disconnect(self._on_auth_failed)
            except RuntimeError:
                pass
            self._auth_worker = None

    def _on_capture_done(self, face_imgs: list):
        """[중요] 캡처 완료 시 모드에 따라 처리."""
        self._stop_thread()

        if self._mode == MODE_REGISTER:
            _play_voice("reg_face_done.mp3")
            self._last_face_imgs = face_imgs
            self._sub_lbl.setText("저장 중...")
            self._save_worker = _EmbeddingSaveWorker(face_imgs, parent=self)
            self._save_worker.done.connect(self._on_save_done)
            self._save_worker.start()
        else:
            # 이전 AuthWorker 시그널 끊기 (capture_done 중복 호출 방어)
            self._stop_auth_worker()
            
            # [FIX] 인증 시작 전 오버레이 스타일 초기화 (재시도 시 잔상 방지)
            self._processing_overlay.setStyleSheet("background-color: #1e293b;")
            self._proc_msg.setText("사용자 확인 중입니다...\n잠시만 기다려 주세요")
            self._proc_msg.setStyleSheet("color: white;")
            
            # 인증 모드: 카메라 숨기고 추론 시작
            self._processing_overlay.show()
            self._auth_worker = _AuthWorker(face_imgs, parent=self)
            self._auth_worker.success.connect(self._on_auth_success)
            self._auth_worker.failed.connect(self._on_auth_failed)
            self._auth_worker.start()

    def _on_auth_success(self, user: str, score: float):
        if self._auth_result_handled:
            return
        self._auth_result_handled = True
        # 실패 후 뒤늦게 성공 신호가 오는 경우 지문 전환 타이머 취소
        if self._fingerprint_timer is not None:
            self._fingerprint_timer.stop()
            self._fingerprint_timer = None
        # 실패 오버레이가 잠깐 표시됐을 수 있으므로 원래 스타일로 복원
        self._processing_overlay.setStyleSheet("background-color: #1e293b;")
        self._proc_msg.setStyleSheet("color: white;")
        self._processing_overlay.hide()
        print(f"\n[AUTH_RESULT] 성공: {user} (최종 점수: {score:.4f})")
        if self._app:
            self._app.current_session["face_verified"] = True
            self._app.current_session["similarity_score"] = score
        result = self._app.screens["auth_result"]
        result.set_result(success=True, user=user)
        self._app.show_screen("auth_result")

    def _on_auth_failed(self):
        self._stop_thread()
        print(f"\n[AUTH_RESULT] 실패: 일치하는 사용자를 찾을 수 없거나 임계값 미달")
        self._processing_overlay.setStyleSheet("background-color: #3a1a1a;")
        self._proc_msg.setText("얼굴 인증에 실패했습니다\n지문 인증으로 전환합니다...")
        self._proc_msg.setStyleSheet("color: #fca5a5;")
        self._processing_overlay.show()
        self._fingerprint_timer = QTimer(self)
        self._fingerprint_timer.setSingleShot(True)
        self._fingerprint_timer.timeout.connect(self._go_fingerprint_auth)
        self._fingerprint_timer.start(2000)

    def _go_fingerprint_auth(self):
        self._fingerprint_timer = None
        if self._auth_result_handled:  # success가 먼저 처리된 경우 무시
            return
        self._processing_overlay.hide()
        self._processing_overlay.setStyleSheet("background-color: #1e293b;")
        self._proc_msg.setStyleSheet("color: white;")
        if self._app:
            self._app.show_screen("fingerprint_auth")

    def _on_progress(self, count: int):
        phase_in_count = ((count - 1) % 4) + 1
        self._sub_lbl.setText(f"촬영 중...  {phase_in_count} / 4")

    def _on_phase_changed(self, phase_idx: int, direction: str):
        _DIRECTION_VOICE = {
            "정면": "reg_face_front.mp3",
            "위": "reg_face_up.mp3",
            "아래": "reg_face_down.mp3",
            "왼쪽": "reg_face_left.mp3",
            "오른쪽": "reg_face_right.mp3",
        }
        voice = _DIRECTION_VOICE.get(direction)
        if voice:
            _play_voice(voice)

        if phase_idx < 0:
            # 카운트다운 중 (-2, -1 순서로 옴)
            countdown = abs(phase_idx)
            self._sub_lbl.setText(f"다음 방향 준비: {direction}  ({countdown}초)")
            self._sub_lbl.setStyleSheet("color: #fbbf24; background: transparent;")
        else:
            self._sub_lbl.setText(f"{direction}을(를) 바라봐 주세요")
            self._sub_lbl.setStyleSheet("color: #93c5fd; background: transparent;")

    def _on_save_done(self, ok: bool):
        if ok:
            if self._app: self._app.show_screen("fingerprint_register")
        else:
            self._upload_error_overlay.show()

    def _on_upload_retry(self):
        self._upload_error_overlay.hide()
        self._sub_lbl.setText("재업로드 중...")
        self._save_worker = _EmbeddingSaveWorker(self._last_face_imgs, parent=self)
        self._save_worker.done.connect(self._on_save_done)
        self._save_worker.start()

    def _on_upload_continue(self):
        self._upload_error_overlay.hide()
        if self._app: self._app.show_screen("fingerprint_register")
