"""
얼굴 인증 통합 테스트 스크립트
실행: raspberry/ 디렉토리에서 python test_face_auth.py

단축키 (대기 화면)
  1 = 사용자 등록  (20프레임 캡처 → 평균 임베딩 → 서버+로컬 저장)
  2 = 인증 테스트  (15프레임 다수결 판정)
  3 = 사용자 삭제  (서버+로컬 임베딩 전체 삭제)
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
    CAMERA_WIDTH, CAMERA_HEIGHT, FACE_MATCH_THRESHOLD, DB_DIR,
)

# ── 상수 ──────────────────────────────────────────────────────────────────────
_FACE_MARGIN        = 0.2
_CENTER_TOL         = 0.15

# 등록
_REG_TARGET         = 20
_REG_COOLDOWN       = 0.6    # 캡처 간격(초)
_PHASES             = ["정면", "위", "아래", "왼쪽", "오른쪽"]
_PHOTOS_PER_PHASE   = 4

# 인증
_AUTH_MAX_CAPTURE   = 15
_AUTH_CAPTURE_INT   = 0.13
_AUTH_VOTE_MIN      = 0.45
_AUTH_TIMEOUT       = 10

_USER_DB_PATH = os.path.join(DB_DIR, "user_db.json")

# ── 모드 ──────────────────────────────────────────────────────────────────────
_M_STANDBY  = "standby"
_M_REGISTER = "register"
_M_AUTH     = "auth"
_M_DELETE   = "delete"
_M_DONE     = "done"


# ══════════════════════════ 공통 유틸 ═════════════════════════════════════════

def _is_centered(face, fw: int) -> bool:
    x, y, w, h = face
    return abs((x + w / 2) - fw / 2) < fw * _CENTER_TOL


def _cosine(a, b) -> float:
    d = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / d) if d else 0.0


def _get_embedding(face_img):
    from face_recognition.model_loader import get_model
    m = get_model()
    if m is None:
        raise RuntimeError("모델 미로드")
    return m.predict(face_img)


def _crop(frame, face, fh, fw):
    x, y, w, h = face
    mx, my = int(w * _FACE_MARGIN), int(h * _FACE_MARGIN)
    x1, y1 = max(0, x - mx), max(0, y - my)
    x2, y2 = min(fw, x + w + mx), min(fh, y + h + my)
    c = frame[y1:y2, x1:x2]
    return c if c.size > 0 else None


def _load_embeddings() -> dict:
    try:
        from api.client import fetch_face_embeddings
        records = fetch_face_embeddings()
        result = {}
        for r in records:
            vec = r["face_vector"]
            if isinstance(vec, str):
                vec = json.loads(vec)
            result[f"patient_{r['patient_id']}_{r['face_id']}"] = np.array(vec, dtype=np.float32)
        if result:
            return result
    except Exception:
        pass
    try:
        with open(_USER_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: np.array(v, dtype=np.float32) for k, v in data.items()}
    except Exception:
        return {}


# ══════════════════════════ 그리기 헬퍼 ══════════════════════════════════════

def _txt(img, text, pos, scale=0.7, color=(220, 220, 220), bold=False):
    t = cv2.FONT_HERSHEY_SIMPLEX
    th = 2 if bold else 1
    cv2.putText(img, text, pos, t, scale, (10, 10, 10), th + 2)
    cv2.putText(img, text, pos, t, scale, color, th)


def _panel(img, y0, y1, alpha=0.55):
    fh, fw = img.shape[:2]
    ov = img.copy()
    cv2.rectangle(ov, (0, y0), (fw, y1), (15, 15, 15), -1)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)


def _progress_bar(img, filled: float, y: int, color=(0, 200, 0)):
    fh, fw = img.shape[:2]
    bx, bw, bh = 10, fw - 20, 12
    cv2.rectangle(img, (bx, y), (bx + bw, y + bh), (60, 60, 60), -1)
    if filled > 0:
        cv2.rectangle(img, (bx, y), (bx + int(bw * filled), y + bh), color, -1)
    cv2.rectangle(img, (bx, y), (bx + bw, y + bh), (120, 120, 120), 1)


# ══════════════════════════ 화면별 렌더러 ════════════════════════════════════

def _draw_standby(frame, emb_count: int):
    d = frame.copy()
    fh, fw = d.shape[:2]
    _panel(d, 0, 85)
    _txt(d, "[ Face Test ]", (10, 30), 0.85, (255, 255, 100), bold=True)
    emb_str = f"Embeddings: {emb_count}" if emb_count else "Embeddings: 없음 (등록 필요)"
    emb_col = (100, 220, 100) if emb_count else (80, 80, 255)
    _txt(d, emb_str, (10, 58), 0.62, emb_col)
    _txt(d, f"Threshold: {FACE_MATCH_THRESHOLD}   VoteRatio: {_AUTH_VOTE_MIN}", (300, 58), 0.62)

    # 중앙 메뉴
    cx, cy = fw // 2, fh // 2
    ov = d.copy()
    cv2.rectangle(ov, (cx - 220, cy - 60), (cx + 220, cy + 90), (10, 10, 10), -1)
    cv2.addWeighted(ov, 0.6, d, 0.4, 0, d)

    _txt(d, "1  Register    2  Authenticate    3  Delete",
         (cx - 210, cy - 20), 0.7, (200, 200, 200), bold=True)
    _txt(d, "Q  Quit", (cx - 30, cy + 30), 0.7, (160, 160, 160))
    return d


def _draw_register(frame, phase: str, captured: int, status: str):
    d = frame.copy()
    fh, fw = d.shape[:2]
    _panel(d, 0, 100)
    _txt(d, "REGISTER", (10, 30), 0.85, (100, 255, 200), bold=True)
    _txt(d, f"Direction: {phase}   Captured: {captured}/{_REG_TARGET}", (10, 58), 0.68)
    _txt(d, status, (10, 84), 0.62, (200, 220, 100))
    _progress_bar(d, captured / _REG_TARGET, fh - 20, color=(0, 200, 180))
    return d


def _draw_auth(frame, face, centered, score, votes, total, remaining):
    d = frame.copy()
    fh, fw = d.shape[:2]

    if face is not None:
        x, y, w, h = face
        bc = (0, 220, 0) if centered else (0, 200, 200)
        cv2.rectangle(d, (x, y), (x + w, y + h), bc, 2)
        if score is not None:
            sc = (0, 220, 0) if score >= FACE_MATCH_THRESHOLD else (0, 100, 255)
            _txt(d, f"{score:.3f}", (x, max(y - 8, 18)), 0.75, sc, bold=True)

    _panel(d, 0, 100)
    _txt(d, "AUTH", (10, 30), 0.85, (100, 220, 255), bold=True)
    ratio_pct = f"{votes/max(total,1)*100:.0f}%"
    _txt(d, f"Captured: {total}/{_AUTH_MAX_CAPTURE}   Votes: {votes} ({ratio_pct})", (10, 58), 0.68)
    _txt(d, f"Timeout: {remaining:.1f}s", (10, 84), 0.65, (200, 200, 100))

    bar_col = (0, 200, 0) if (votes / max(total, 1)) >= _AUTH_VOTE_MIN else (0, 100, 255)
    _progress_bar(d, total / _AUTH_MAX_CAPTURE, fh - 20, color=bar_col)
    return d


def _draw_done(frame, mode: str, passed: bool, detail: str):
    d = frame.copy()
    fh, fw = d.shape[:2]
    tint = (10, 40, 10) if passed else (40, 10, 10)
    ov = d.copy()
    cv2.rectangle(ov, (0, 0), (fw, fh), tint, -1)
    cv2.addWeighted(ov, 0.45, d, 0.55, 0, d)

    if mode == _M_DELETE:
        label = "DELETED" if passed else "DELETE FAIL"
        color = (80, 200, 255) if passed else (60, 60, 230)
    elif mode == _M_REGISTER:
        label = "REGISTERED" if passed else "UPLOAD FAIL"
        color = (60, 230, 60) if passed else (60, 60, 230)
    else:
        label = "SUCCESS" if passed else "FAIL"
        color = (60, 230, 60) if passed else (60, 60, 230)

    (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 2.2, 4)
    rx = (fw - tw) // 2
    ry = fh // 2 - 20
    cv2.putText(d, label, (rx, ry), cv2.FONT_HERSHEY_DUPLEX, 2.2, (0, 0, 0), 7)
    cv2.putText(d, label, (rx, ry), cv2.FONT_HERSHEY_DUPLEX, 2.2, color, 4)

    _txt(d, detail, (fw // 2 - 180, ry + 50), 0.7, (220, 220, 220))
    _txt(d, "1/2/3 : 다시 선택    Q : 종료", (fw // 2 - 160, ry + 86), 0.7, (180, 180, 180))
    return d


def _draw_processing(frame, msg: str):
    d = frame.copy()
    fh, fw = d.shape[:2]
    ov = d.copy()
    cv2.rectangle(ov, (0, 0), (fw, fh), (10, 10, 30), -1)
    cv2.addWeighted(ov, 0.55, d, 0.45, 0, d)
    _txt(d, msg, (fw // 2 - 120, fh // 2), 0.9, (200, 200, 255), bold=True)
    return d


# ══════════════════════════ 백그라운드 작업 ═══════════════════════════════════

def _bg_upload(embeddings: list, callback):
    """평균 임베딩 계산 → 로컬 저장 → 서버 업로드 (별도 스레드)."""
    def _run():
        try:
            mean_emb = np.mean(np.array(embeddings), axis=0).tolist()
            try:
                with open(_USER_DB_PATH, "r", encoding="utf-8") as f:
                    db = json.load(f)
            except Exception:
                db = {}
            db["_latest"] = mean_emb
            with open(_USER_DB_PATH, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)

            from api.client import upload_face_embedding
            from auth.authenticate import invalidate_embedding_cache
            ok = upload_face_embedding(mean_emb)
            invalidate_embedding_cache()
            callback(ok)
        except Exception as e:
            print(f"[UPLOAD ERR] {e}")
            callback(False)

    threading.Thread(target=_run, daemon=True).start()


def _bg_delete(callback):
    """서버 + 로컬 임베딩 삭제 (별도 스레드)."""
    def _run():
        srv_ok = False
        try:
            from api.client import delete_face_embedding
            srv_ok = delete_face_embedding()
        except Exception as e:
            print(f"[DELETE ERR] server: {e}")
        try:
            with open(_USER_DB_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception as e:
            print(f"[DELETE ERR] local: {e}")
        try:
            from auth.authenticate import invalidate_embedding_cache
            invalidate_embedding_cache()
        except Exception:
            pass
        callback(srv_ok)

    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════ 메인 ══════════════════════════════════════════════

def run_test():
    from face_detection.mediapipe_detector import detect_face
    from camera.camera import get_frame, release_camera

    print("=" * 55)
    print("  얼굴 테스트  1=등록  2=인증  3=삭제  Q=종료")
    print(f"  임계값: {FACE_MATCH_THRESHOLD}   투표 비율: {_AUTH_VOTE_MIN}")
    print("=" * 55)

    # 카메라 초기화
    print("[CAM] 카메라 초기화 중...")
    deadline = time.time() + 5.0
    while time.time() < deadline:
        f = get_frame()
        if f is not None:
            print("[CAM] 준비 완료")
            break
        time.sleep(0.2)
    else:
        print("[ERROR] 카메라 초기화 실패")
        release_camera()
        return

    # ── 공유 상태 ──────────────────────────────────────────────────────────────
    mode         = _M_STANDBY
    embeddings   = _load_embeddings()

    # 등록용
    reg_imgs     = []
    reg_phase    = 0
    reg_captured = 0
    reg_last_t   = 0.0
    reg_status   = "얼굴을 정면으로 향해주세요"

    # 인증용
    auth_imgs    = []
    auth_scores  = []
    auth_votes   = 0
    auth_start   = None
    auth_last_t  = 0.0

    # 완료용
    done_mode    = ""
    done_passed  = False
    done_detail  = ""

    # 비동기 결과 수신용
    _async_result = [None]   # [None | bool]

    def _on_upload_done(ok: bool):
        _async_result[0] = ok

    def _on_delete_done(ok: bool):
        _async_result[0] = ok

    def _reset_reg():
        nonlocal reg_imgs, reg_phase, reg_captured, reg_last_t, reg_status
        reg_imgs, reg_phase, reg_captured, reg_last_t = [], 0, 0, 0.0
        reg_status = f"얼굴을 '{_PHASES[0]}' 방향으로 향해주세요"

    def _reset_auth():
        nonlocal auth_imgs, auth_scores, auth_votes, auth_start, auth_last_t
        auth_imgs, auth_scores, auth_votes, auth_start, auth_last_t = [], [], 0, None, 0.0

    # ── 메인 루프 ──────────────────────────────────────────────────────────────
    try:
        while True:
            frame = get_frame()
            if frame is None:
                time.sleep(0.02)
                continue

            fh, fw = frame.shape[:2]
            now = time.time()

            # ── 대기 화면 ────────────────────────────────────────────────────
            if mode == _M_STANDBY:
                disp = _draw_standby(frame, len(embeddings))

            # ── 등록 진행 ────────────────────────────────────────────────────
            elif mode == _M_REGISTER:
                small = cv2.resize(frame, (320, 240))
                faces = detect_face(small)
                face_detected = None

                if faces:
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
                    face_detected = (x, y, w, h)
                    centered = _is_centered(face_detected, fw)

                    # 얼굴 박스
                    cv2.rectangle(frame, (x, y), (x + w, y + h),
                                  (0, 220, 0) if centered else (0, 200, 200), 2)

                    if centered and now - reg_last_t >= _REG_COOLDOWN:
                        c = _crop(frame, face_detected, fh, fw)
                        if c is not None:
                            reg_imgs.append(c)
                            reg_captured += 1
                            reg_last_t = now
                            print(f"[REG] {reg_captured}/{_REG_TARGET}  phase={_PHASES[reg_phase]}")

                            # 방향 전환
                            next_phase = reg_captured // _PHOTOS_PER_PHASE
                            if next_phase != reg_phase and next_phase < len(_PHASES):
                                reg_phase = next_phase
                                reg_status = f"'{_PHASES[reg_phase]}' 방향으로 향해주세요"

                    if reg_captured >= _REG_TARGET:
                        print(f"[REG] 캡처 완료 ({_REG_TARGET}장) — 서버 업로드 중...")
                        mode = _M_DONE   # processing overlay 먼저 보여줌
                        done_mode   = _M_REGISTER
                        done_passed = False
                        done_detail = "서버 업로드 중..."
                        _async_result[0] = None
                        _bg_upload(reg_imgs, _on_upload_done)

                disp = _draw_register(frame, _PHASES[reg_phase], reg_captured, reg_status)

            # ── 인증 진행 ────────────────────────────────────────────────────
            elif mode == _M_AUTH:
                if auth_start is None:
                    auth_start = now

                elapsed   = now - auth_start
                remaining = max(0.0, _AUTH_TIMEOUT - elapsed)
                total     = len(auth_imgs)

                face_detected = None
                centered      = False
                last_score    = None

                small = cv2.resize(frame, (320, 240))
                faces = detect_face(small)
                if faces:
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
                    face_detected = (x, y, w, h)
                    centered = _is_centered(face_detected, fw)

                    if centered and now - auth_last_t >= _AUTH_CAPTURE_INT:
                        c = _crop(frame, face_detected, fh, fw)
                        if c is not None:
                            try:
                                emb = _get_embedding(c)
                                best = max(_cosine(emb, ref) for ref in embeddings.values())
                                last_score = best
                                auth_imgs.append(c)
                                auth_scores.append(best)
                                if best >= FACE_MATCH_THRESHOLD:
                                    auth_votes += 1
                                auth_last_t = now
                                total = len(auth_imgs)
                                print(
                                    f"[AUTH {total:02d}/{_AUTH_MAX_CAPTURE}] "
                                    f"score={best:.4f}  votes={auth_votes}/{total}"
                                )
                            except Exception as e:
                                print(f"[EMBED ERR] {e}")

                finished      = total >= _AUTH_MAX_CAPTURE
                timeout_empty = elapsed >= _AUTH_TIMEOUT and total == 0
                timeout_some  = elapsed >= _AUTH_TIMEOUT and total > 0

                if finished or timeout_some or timeout_empty:
                    ratio  = auth_votes / total if total else 0
                    passed = ratio >= _AUTH_VOTE_MIN and total > 0
                    avg    = float(np.mean(auth_scores)) if auth_scores else 0.0
                    label  = "SUCCESS" if passed else "FAIL"
                    print()
                    print("=" * 45)
                    print(f"  판정: {label}")
                    print(f"  프레임: {total}   투표: {auth_votes}   비율: {ratio:.2%}")
                    print(f"  평균 유사도: {avg:.4f}   임계값: {FACE_MATCH_THRESHOLD}")
                    print("=" * 45)
                    mode        = _M_DONE
                    done_mode   = _M_AUTH
                    done_passed = passed
                    done_detail = (
                        f"Votes: {auth_votes}/{total} ({ratio:.0%})   AvgScore: {avg:.4f}"
                        if total else "얼굴 미감지 — 타임아웃"
                    )

                disp = _draw_auth(frame, face_detected, centered, last_score,
                                  auth_votes, len(auth_imgs), remaining)

            # ── 삭제 진행 ────────────────────────────────────────────────────
            elif mode == _M_DELETE:
                # _bg_delete 호출 후 즉시 DONE으로 전환하므로 이 분기는 처리 중 표시용
                disp = _draw_processing(frame, "삭제 중...")

            # ── 완료 / 업로드 대기 ───────────────────────────────────────────
            elif mode == _M_DONE:
                # 비동기 결과 확인
                if _async_result[0] is not None:
                    ok = _async_result[0]
                    _async_result[0] = None
                    if done_mode == _M_REGISTER:
                        done_passed = ok
                        done_detail = (
                            "서버+로컬 저장 완료" if ok else "로컬 저장됨 (서버 업로드 실패)"
                        )
                        embeddings = _load_embeddings()
                        print(f"[REG] {'완료' if ok else '서버 실패'}")
                    elif done_mode == _M_DELETE:
                        done_passed = True   # 로컬은 항상 삭제됨
                        done_detail = "서버+로컬 삭제 완료" if ok else "로컬만 삭제됨 (서버 오류)"
                        embeddings = _load_embeddings()
                        print(f"[DEL] {'완료' if ok else '서버 실패'}")

                disp = _draw_done(frame, done_mode, done_passed, done_detail)

            else:
                disp = frame.copy()

            cv2.imshow("Face Test", disp)

            # ── 키 처리 ──────────────────────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            elif key == ord("1") and mode in (_M_STANDBY, _M_DONE):
                print("\n[MODE] 등록 시작\n")
                _reset_reg()
                mode = _M_REGISTER

            elif key == ord("2") and mode in (_M_STANDBY, _M_DONE):
                if not embeddings:
                    print("[WARN] 저장된 임베딩 없음 — 먼저 1번으로 등록하세요.")
                else:
                    print("\n[MODE] 인증 시작\n")
                    _reset_auth()
                    mode = _M_AUTH

            elif key == ord("3") and mode in (_M_STANDBY, _M_DONE):
                print("\n[MODE] 삭제 시작\n")
                mode        = _M_DELETE
                done_mode   = _M_DELETE
                done_passed = False
                done_detail = "삭제 중..."
                _async_result[0] = None
                _bg_delete(_on_delete_done)
                mode = _M_DONE   # 즉시 완료 화면으로 (결과는 비동기 수신)

    finally:
        release_camera()
        cv2.destroyAllWindows()
        print("[CAM] 종료")


if __name__ == "__main__":
    run_test()
