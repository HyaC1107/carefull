"""
얼굴 인증 통합 테스트 (PyQt5 기반) - 고도화 버전
실행: raspberry/ 디렉토리에서 python test_face_auth.py

개선사항:
  - BGR->RGB 변환 (정확도 향상)
  - 정사각형 고정 배율 크롭 (거리 편차 감소)
  - 멀티 템플릿 저장 및 매칭 (상위 10개 프레임)

단축키
  1 = 사용자 등록
  2 = 인증 테스트
  3 = 사용자 삭제
  Q = 종료
"""

import json
import os
import sys
import threading
import time

import cv2
import numpy as np

# ── 경로 ──────────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from config.settings import (
    CAMERA_WIDTH, CAMERA_HEIGHT, FACE_MATCH_THRESHOLD,
    DB_DIR, SCREEN_WIDTH, SCREEN_HEIGHT,
)

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QMetaObject, Q_ARG
from PyQt5.QtGui import QColor, QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

# ── 상수 ──────────────────────────────────────────────────────────────────────
_CENTER_TOL        = 0.15
_REG_TARGET        = 20
_REG_COOLDOWN      = 0.6
_PHASES            = ["정면", "위", "아래", "왼쪽", "오른쪽"]
_PHOTOS_PER_PHASE  = 4
_AUTH_MAX_CAPTURE  = 15
_AUTH_CAPTURE_INT  = 0.13
_AUTH_VOTE_MIN     = 0.3
_AUTH_TIMEOUT      = 10

_USER_DB_PATH = os.path.join(DB_DIR, "user_db.json")

_M_STANDBY  = "standby"
_M_REGISTER = "register"
_M_AUTH     = "auth"
_M_DONE     = "done"


# ══════════════════════════ 유틸 ══════════════════════════════════════════════

def _is_centered(face, fw):
    x, y, w, h = face
    return abs((x + w / 2) - fw / 2) < fw * _CENTER_TOL


def _cosine(a, b):
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / d) if d else 0.0


def _get_embedding(img_bgr):
    from face_recognition.model_loader import get_model
    m = get_model()
    if m is None:
        raise RuntimeError("모델 미로드")
    
    # ── 개선: BGR -> RGB 변환 적용 ──
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return m.predict(img_rgb)


def _crop_square(frame, face, fh, fw):
    """개선: 정사각형 고정 배율 크롭 (거리/스케일 편차 방지)"""
    x, y, w, h = face
    cx, cy = x + w / 2, y + h / 2
    
    # 얼굴 크기의 1.45배 정사각형 영역 계산
    side = max(w, h) * 1.45
    x1 = int(max(0, cx - side / 2))
    y1 = int(max(0, cy - side / 2))
    x2 = int(min(fw, cx + side / 2))
    y2 = int(min(fh, cy + side / 2))
    
    c = frame[y1:y2, x1:x2]
    return c if c.size > 0 else None


def _load_embeddings():
    """개선: 단일 벡터 및 멀티 벡터(리스트) 모두 대응 로직"""
    try:
        with open(_USER_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        result = {}
        for k, v in data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], list):
                # 멀티 템플릿 리스트
                result[k] = [np.array(vec, dtype=np.float32) for vec in v]
            else:
                # 단일 벡터
                result[k] = np.array(v, dtype=np.float32)
        return result
    except Exception:
        return {}


# ══════════════════════════ OpenCV 오버레이 헬퍼 ══════════════════════════════

def _cv_txt(img, text, pos, scale=0.7, color=(220, 220, 220), bold=False):
    th = 2 if bold else 1
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (10, 10, 10), th + 2)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, th)


def _cv_panel(img, y0, y1, alpha=0.55):
    ov = img.copy()
    cv2.rectangle(ov, (0, y0), (img.shape[1], y1), (15, 15, 15), -1)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)


def _cv_bar(img, filled, y, color=(0, 200, 0)):
    fw = img.shape[1]
    bx, bw, bh = 10, fw - 20, 12
    cv2.rectangle(img, (bx, y), (bx + bw, y + bh), (60, 60, 60), -1)
    if filled > 0:
        cv2.rectangle(img, (bx, y), (bx + int(bw * filled), y + bh), color, -1)
    cv2.rectangle(img, (bx, y), (bx + bw, y + bh), (120, 120, 120), 1)


def _render_standby(frame, emb_count):
    d = frame.copy()
    fh, fw = d.shape[:2]
    _cv_panel(d, 0, 95)
    _cv_txt(d, "[ Face Test - High Precision ]", (10, 35), 0.9, (255, 255, 100), bold=True)
    emb_col = (80, 220, 80) if emb_count else (80, 80, 255)
    emb_str = f"Templates: {emb_count}" if emb_count else "Templates: 없음 (1번 등록 필요)"
    _cv_txt(d, emb_str, (10, 65), 0.7, emb_col)
    _cv_txt(d, f"Threshold: {FACE_MATCH_THRESHOLD}   VoteRatio: {_AUTH_VOTE_MIN}", (10, 90), 0.65)
    return d


def _render_register(frame, phase, captured, status):
    d = frame.copy()
    fh = d.shape[0]
    _cv_panel(d, 0, 105)
    _cv_txt(d, "REGISTER (Square-Crop)", (10, 35), 0.95, (100, 255, 200), bold=True)
    _cv_txt(d, f"Direction: {phase}   Captured: {captured}/{_REG_TARGET}", (10, 65), 0.75)
    _cv_txt(d, status, (10, 95), 0.68, (200, 220, 100))
    _cv_bar(d, captured / _REG_TARGET, fh - 22, color=(0, 200, 180))
    return d


def _render_auth(frame, face, centered, score, votes, total, remaining):
    d = frame.copy()
    fh = d.shape[0]
    if face is not None:
        x, y, w, h = face
        bc = (0, 220, 0) if centered else (0, 200, 200)
        cv2.rectangle(d, (x, y), (x + w, y + h), bc, 2)
        if score is not None:
            sc = (0, 220, 0) if score >= FACE_MATCH_THRESHOLD else (0, 100, 255)
            _cv_txt(d, f"{score:.3f}", (x, max(y - 8, 18)), 0.8, sc, bold=True)
    _cv_panel(d, 0, 105)
    _cv_txt(d, "AUTH (Multi-Match)", (10, 35), 0.95, (100, 220, 255), bold=True)
    pct = f"{votes/max(total,1)*100:.0f}%"
    _cv_txt(d, f"Captured: {total}/{_AUTH_MAX_CAPTURE}   Votes: {votes} ({pct})", (10, 65), 0.75)
    _cv_txt(d, f"Timeout: {remaining:.1f}s", (10, 95), 0.7, (200, 200, 100))
    bar_col = (0, 200, 0) if (votes / max(total, 1)) >= _AUTH_VOTE_MIN else (0, 100, 255)
    _cv_bar(d, total / _AUTH_MAX_CAPTURE, fh - 22, color=bar_col)
    return d


def _render_done(frame, mode, passed, detail):
    d = frame.copy()
    fh, fw = d.shape[:2]
    tint = (10, 40, 10) if passed else (40, 10, 10)
    ov = d.copy()
    cv2.rectangle(ov, (0, 0), (fw, fh), tint, -1)
    cv2.addWeighted(ov, 0.45, d, 0.55, 0, d)

    if mode == _M_REGISTER:
        label, col = ("REGISTERED", (60, 230, 60)) if passed else ("FAIL", (60, 60, 230))
    elif mode == "delete":
        label, col = ("DELETED", (80, 200, 255)) if passed else ("FAIL", (60, 60, 230))
    else:
        label, col = ("SUCCESS", (60, 230, 60)) if passed else ("FAIL", (60, 60, 230))

    (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 2.2, 4)
    rx, ry = (fw - tw) // 2, fh // 2 - 20
    cv2.putText(d, label, (rx, ry), cv2.FONT_HERSHEY_DUPLEX, 2.2, (0, 0, 0), 7)
    cv2.putText(d, label, (rx, ry), cv2.FONT_HERSHEY_DUPLEX, 2.2, col, 4)
    _cv_txt(d, detail, (fw // 2 - 200, ry + 52), 0.72, (220, 220, 220))
    _cv_txt(d, "1/2/3 : next    Q : quit", (fw // 2 - 130, ry + 88), 0.72, (180, 180, 180))
    return d


def _render_processing(frame, msg):
    d = frame.copy()
    fh, fw = d.shape[:2]
    ov = d.copy()
    cv2.rectangle(ov, (0, 0), (fw, fh), (10, 10, 30), -1)
    cv2.addWeighted(ov, 0.55, d, 0.45, 0, d)
    _cv_txt(d, msg, (fw // 2 - 130, fh // 2), 0.95, (200, 200, 255), bold=True)
    return d


# ══════════════════════════ PyQt5 메인 윈도우 ═════════════════════════════════

class TestWindow(QWidget):
    _cmd_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Face Test Lab")
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet("background: black;")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignCenter)
        root.addWidget(self._img_lbl, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 4, 8, 8)
        btn_row.setSpacing(8)

        _btn_style = """
            QPushButton {{
                background-color: {bg};
                color: white;
                font-size: 26px;
                font-weight: bold;
                border-radius: 12px;
                border: none;
            }}
            QPushButton:pressed {{ background-color: {press}; }}
            QPushButton:disabled {{ background-color: #444; color: #888; }}
        """
        self._btn1 = QPushButton("1  등록")
        self._btn1.setFixedHeight(64)
        self._btn1.setStyleSheet(_btn_style.format(bg="#0d6efd", press="#0a58ca"))
        self._btn1.clicked.connect(lambda: self._handle_cmd("1"))

        self._btn2 = QPushButton("2  인증")
        self._btn2.setFixedHeight(64)
        self._btn2.setStyleSheet(_btn_style.format(bg="#198754", press="#146c43"))
        self._btn2.clicked.connect(lambda: self._handle_cmd("2"))

        self._btn3 = QPushButton("3  삭제")
        self._btn3.setFixedHeight(64)
        self._btn3.setStyleSheet(_btn_style.format(bg="#dc3545", press="#b02a37"))
        self._btn3.clicked.connect(lambda: self._handle_cmd("3"))

        btn_q = QPushButton("Q  종료")
        btn_q.setFixedHeight(64)
        btn_q.setFixedWidth(120)
        btn_q.setStyleSheet(_btn_style.format(bg="#6c757d", press="#565e64"))
        btn_q.clicked.connect(self.close)

        btn_row.addWidget(self._btn1)
        btn_row.addWidget(self._btn2)
        btn_row.addWidget(self._btn3)
        btn_row.addWidget(btn_q)
        root.addLayout(btn_row)

        self._mode       = _M_STANDBY
        self._embeddings = {}
        self._async_res  = [None]

        self._reg_imgs    = []
        self._reg_phase   = 0
        self._reg_captured= 0
        self._reg_last_t  = 0.0
        self._reg_status  = f"얼굴을 '{_PHASES[0]}' 방향으로 향해주세요"

        self._auth_imgs   = []
        self._auth_scores = []
        self._auth_votes  = 0
        self._auth_start  = None
        self._auth_last_t = 0.0

        self._done_mode   = ""
        self._done_passed = False
        self._done_detail = ""

        from camera.camera import get_frame
        self._get_frame = get_frame
        from face_detection.mediapipe_detector import detect_face
        self._detect_face = detect_face

        self._embeddings = _load_embeddings()
        
        self._cmd_signal.connect(self._handle_cmd)
        t = threading.Thread(target=self._stdin_reader, daemon=True)
        t.start()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def _stdin_reader(self):
        while True:
            try:
                line = sys.stdin.readline()
                if not line: break
                cmd = line.strip().lower()
                if cmd: self._cmd_signal.emit(cmd)
            except Exception: break

    def _handle_cmd(self, cmd: str):
        if cmd == "q": self.close()
        elif cmd == "1" and self._mode in (_M_STANDBY, _M_DONE): self._start_register()
        elif cmd == "2" and self._mode in (_M_STANDBY, _M_DONE): self._start_auth()
        elif cmd == "3" and self._mode in (_M_STANDBY, _M_DONE): self._start_delete()

    def keyPressEvent(self, event):
        mapping = {Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3", Qt.Key_Q: "q"}
        cmd = mapping.get(event.key())
        if cmd: self._handle_cmd(cmd)

    def _set_buttons_enabled(self, enabled: bool):
        self._btn1.setEnabled(enabled)
        self._btn2.setEnabled(enabled)
        self._btn3.setEnabled(enabled)

    def _start_register(self):
        self._reg_imgs     = []
        self._reg_phase    = 0
        self._reg_captured = 0
        self._reg_last_t   = 0.0
        self._reg_status   = f"얼굴을 '{_PHASES[0]}' 방향으로 향해주세요"
        self._set_buttons_enabled(False)
        self._mode = _M_REGISTER

    def _start_auth(self):
        if not self._embeddings: return
        self._auth_imgs   = []
        self._auth_scores = []
        self._auth_votes  = 0
        self._auth_start  = None
        self._auth_last_t = 0.0
        self._set_buttons_enabled(False)
        self._mode = _M_AUTH

    def _start_delete(self):
        self._set_buttons_enabled(False)
        self._async_res[0] = None
        self._done_mode   = "delete"
        self._done_passed = False
        self._done_detail = "삭제 중..."
        self._mode = _M_DONE
        def _run():
            try:
                if os.path.exists(_USER_DB_PATH): os.remove(_USER_DB_PATH)
                from auth.authenticate import invalidate_embedding_cache
                invalidate_embedding_cache()
                self._async_res[0] = True
            except Exception: self._async_res[0] = False
        threading.Thread(target=_run, daemon=True).start()

    def _tick(self):
        frame = self._get_frame()
        if frame is None: return
        fh, fw = frame.shape[:2]
        now = time.time()

        if self._mode == _M_STANDBY:
            disp = _render_standby(frame, len(self._embeddings))
        elif self._mode == _M_REGISTER:
            disp = self._tick_register(frame, fh, fw, now)
        elif self._mode == _M_AUTH:
            disp = self._tick_auth(frame, fh, fw, now)
        elif self._mode == _M_DONE:
            if self._async_res[0] is not None:
                ok = self._async_res[0]
                self._async_res[0] = None
                self._done_passed = ok
                self._embeddings  = _load_embeddings()
                
                # 로그 저장 로직 추가
                if self._done_mode == _M_AUTH:
                    avg_score = float(np.mean(self._auth_scores)) if self._auth_scores else 0.0
                    _save_log("AUTH", ok, self._done_detail, avg_score)
                elif self._done_mode == _M_REGISTER:
                    _save_log("REGISTER", ok, "로컬 저장 완료" if ok else "실패")
                elif self._done_mode == "delete":
                    _save_log("DELETE", ok, "삭제 완료" if ok else "실패")
                
                self._done_detail = "처리 완료" if ok else "처리 실패"
                self._set_buttons_enabled(True)
            disp = _render_done(frame, self._done_mode, self._done_passed, self._done_detail)
        else:
            disp = frame.copy()
        self._show(disp)

    def _tick_register(self, frame, fh, fw, now):
        small = cv2.resize(frame, (320, 240))
        faces = self._detect_face(small)
        if faces:
            sx, sy, sw, sh = faces[0]
            x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
            face = (x, y, w, h)
            centered = _is_centered(face, fw)
            if centered and now - self._reg_last_t >= _REG_COOLDOWN:
                c = _crop_square(frame, face, fh, fw)
                if c is not None:
                    self._reg_imgs.append(c)
                    self._reg_captured += 1
                    self._reg_last_t = now
                    next_phase = self._reg_captured // _PHOTOS_PER_PHASE
                    if next_phase != self._reg_phase and next_phase < len(_PHASES):
                        self._reg_phase = next_phase
                        self._reg_status = f"얼굴을 '{_PHASES[self._reg_phase]}' 방향으로 향해주세요"
            if self._reg_captured >= _REG_TARGET:
                self._done_mode, self._mode = _M_REGISTER, _M_DONE
                self._async_res[0] = None
                imgs = list(self._reg_imgs)
                def _save():
                    try:
                        # 품질 순 상위 10개 추출
                        imgs.sort(key=lambda i: i.shape[0]*i.shape[1], reverse=True)
                        best = imgs[:10]
                        embs = []
                        for i in best:
                            try: embs.append(_get_embedding(i).tolist())
                            except Exception: pass
                        if not embs: self._async_res[0] = False; return
                        try:
                            with open(_USER_DB_PATH, "r") as f: db = json.load(f)
                        except Exception: db = {}
                        db["_latest"] = embs # 멀티 템플릿 저장
                        with open(_USER_DB_PATH, "w") as f: json.dump(db, f, indent=2)
                        from auth.authenticate import invalidate_embedding_cache
                        invalidate_embedding_cache()
                        self._async_res[0] = True
                    except Exception: self._async_res[0] = False
                threading.Thread(target=_save, daemon=True).start()
        return _render_register(frame, _PHASES[self._reg_phase], self._reg_captured, self._reg_status)

    def _tick_auth(self, frame, fh, fw, now):
        if self._auth_start is None: self._auth_start = now
        elapsed, remaining = now - self._auth_start, max(0.0, _AUTH_TIMEOUT - (now - self._auth_start))
        total, face_det, centered, last_score = len(self._auth_imgs), None, False, None
        small = cv2.resize(frame, (320, 240))
        faces = self._detect_face(small)
        if faces:
            sx, sy, sw, sh = faces[0]
            x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
            face_det, centered = (x, y, w, h), _is_centered((x, y, w, h), fw)
            if centered and now - self._auth_last_t >= _AUTH_CAPTURE_INT:
                c = _crop_square(frame, face_det, fh, fw)
                if c is not None:
                    try:
                        emb = _get_embedding(c)
                        # 멀티 템플릿 대응 매칭
                        scores = []
                        for ref in self._embeddings.values():
                            if isinstance(ref, list): scores.append(max(_cosine(emb, r) for r in ref))
                            else: scores.append(_cosine(emb, ref))
                        best = max(scores) if scores else 0.0
                        last_score = best
                        self._auth_imgs.append(c)
                        self._auth_scores.append(best)
                        if best >= FACE_MATCH_THRESHOLD: self._auth_votes += 1
                        self._auth_last_t, total = now, len(self._auth_imgs)
                    except Exception: pass
        if total >= _AUTH_MAX_CAPTURE or (elapsed >= _AUTH_TIMEOUT):
            ratio = self._auth_votes / total if total else 0
            passed = ratio >= _AUTH_VOTE_MIN and total > 0
            self._mode, self._done_mode, self._done_passed = _M_DONE, _M_AUTH, passed
            self._done_detail = f"Votes: {self._auth_votes}/{total} ({ratio:.0%}) Avg: {np.mean(self._auth_scores):.3f}" if total else "Timeout"
            self._set_buttons_enabled(True)
        return _render_auth(frame, face_det, centered, last_score, self._auth_votes, total, remaining)

    def _show(self, bgr):
        h, w, ch = bgr.shape
        q = QImage(bgr.data, w, h, ch * w, QImage.Format_RGB888).rgbSwapped()
        self._img_lbl.setPixmap(QPixmap.fromImage(q).scaled(SCREEN_WIDTH, SCREEN_HEIGHT, Qt.KeepAspectRatio))

    def closeEvent(self, event):
        self._timer.stop()
        from camera.camera import release_camera
        release_camera()
        super().closeEvent(event)

def run_test():
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_test()
ap(QPixmap.fromImage(q).scaled(SCREEN_WIDTH, SCREEN_HEIGHT, Qt.KeepAspectRatio))

    def closeEvent(self, event):
        self._timer.stop()
        from camera.camera import release_camera
        release_camera()
        super().closeEvent(event)

def run_test():
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_test()
ain__":
    run_test()
