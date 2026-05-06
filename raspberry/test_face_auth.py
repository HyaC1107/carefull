"""
얼굴 인증 단독 테스트 스크립트
실행: raspberry/ 디렉토리에서 python test_face_auth.py

단축키
  1 = 인증 시작
  R = 다시 시작 (결과 후)
  Q = 종료
"""

import json
import os
import sys
import time

import cv2
import numpy as np

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from config.settings import (
    CAMERA_WIDTH, CAMERA_HEIGHT, FACE_MATCH_THRESHOLD, DB_DIR,
)

_FACE_MARGIN      = 0.2
_CENTER_TOL       = 0.15
_MAX_CAPTURE      = 15
_CAPTURE_INTERVAL = 0.13
_VOTE_RATIO_MIN   = 0.45
_TIMEOUT_SEC      = 10

_USER_DB_PATH = os.path.join(DB_DIR, "user_db.json")

# 상태
_STATE_STANDBY = "standby"   # 대기 (1 누르기 전)
_STATE_RUNNING = "running"   # 인증 진행 중
_STATE_DONE    = "done"      # 판정 완료


# ── 임베딩 로드 ───────────────────────────────────────────────────────────────

def _load_embeddings() -> dict:
    try:
        from api.client import fetch_face_embeddings
        records = fetch_face_embeddings()
        result = {}
        for r in records:
            vec = r["face_vector"]
            if isinstance(vec, str):
                vec = json.loads(vec)
            key = f"patient_{r['patient_id']}_{r['face_id']}"
            result[key] = np.array(vec, dtype=np.float32)
        if result:
            print(f"[EMB] 서버에서 {len(result)}개 임베딩 로드")
            return result
    except Exception as e:
        print(f"[EMB] 서버 로드 실패 ({e}), 로컬로 대체")

    try:
        with open(_USER_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {k: np.array(v, dtype=np.float32) for k, v in data.items()}
        print(f"[EMB] 로컬 DB에서 {len(result)}개 임베딩 로드")
        return result
    except Exception as e:
        print(f"[EMB] 로컬 DB 로드 실패: {e}")
        return {}


# ── 유틸 ─────────────────────────────────────────────────────────────────────

def _is_centered(face, fw: int) -> bool:
    x, y, w, h = face
    return abs((x + w / 2) - fw / 2) < fw * _CENTER_TOL


def _cosine_similarity(a, b) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom else 0.0


def _get_embedding(face_img):
    from face_recognition.model_loader import get_model
    model = get_model()
    if model is None:
        raise RuntimeError("모델 미로드")
    return model.predict(face_img)


def _crop_face(frame, face, fh, fw):
    x, y, w, h = face
    mx, my = int(w * _FACE_MARGIN), int(h * _FACE_MARGIN)
    x1, y1 = max(0, x - mx), max(0, y - my)
    x2, y2 = min(fw, x + w + mx), min(fh, y + h + my)
    crop = frame[y1:y2, x1:x2]
    return crop if crop.size > 0 else None


# ── 화면 그리기 ───────────────────────────────────────────────────────────────

def _put_text_shadow(img, text, pos, scale, color, thickness=1):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (20, 20, 20), thickness + 2)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def _draw_standby(frame, emb_count: int):
    """대기 화면: 카메라 피드 + 안내 오버레이"""
    disp = frame.copy()
    fh, fw = disp.shape[:2]

    # 반투명 상단 배너
    overlay = disp.copy()
    cv2.rectangle(overlay, (0, 0), (fw, 90), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.55, disp, 0.45, 0, disp)

    _put_text_shadow(disp, "[ Face Auth Test ]", (10, 32), 0.9, (255, 255, 100), 2)
    _put_text_shadow(disp, f"Embeddings: {emb_count}   Threshold: {FACE_MATCH_THRESHOLD}   VoteRatio: {_VOTE_RATIO_MIN}", (10, 60), 0.62, (200, 200, 200))

    # 중앙 안내
    overlay2 = disp.copy()
    box_y = fh // 2 - 40
    cv2.rectangle(overlay2, (fw // 2 - 200, box_y), (fw // 2 + 200, box_y + 70), (10, 10, 10), -1)
    cv2.addWeighted(overlay2, 0.6, disp, 0.4, 0, disp)

    _put_text_shadow(disp, "1  :  Start", (fw // 2 - 70, fh // 2), 1.2, (100, 255, 100), 2)
    _put_text_shadow(disp, "Q  :  Quit", (fw // 2 - 60, fh // 2 + 36), 0.75, (180, 180, 180))

    return disp


def _draw_running(frame, face, centered, score, votes, total, remaining):
    disp = frame.copy()
    fh, fw = disp.shape[:2]

    # 얼굴 박스
    if face is not None:
        x, y, w, h = face
        box_color = (0, 220, 0) if centered else (0, 200, 200)
        cv2.rectangle(disp, (x, y), (x + w, y + h), box_color, 2)
        if score is not None:
            score_color = (0, 220, 0) if score >= FACE_MATCH_THRESHOLD else (0, 100, 255)
            _put_text_shadow(disp, f"{score:.3f}", (x, max(y - 8, 18)), 0.75, score_color, 2)

    # 상단 패널
    overlay = disp.copy()
    cv2.rectangle(overlay, (0, 0), (fw, 100), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.6, disp, 0.4, 0, disp)

    _put_text_shadow(disp, "RUNNING", (10, 30), 0.85, (100, 220, 255), 2)
    _put_text_shadow(disp,
        f"Captured: {total}/{_MAX_CAPTURE}   Votes: {votes}   ({votes/max(total,1)*100:.0f}%)",
        (10, 58), 0.68, (220, 220, 220))
    _put_text_shadow(disp, f"Timeout: {remaining:.1f}s", (10, 84), 0.65, (200, 200, 100))

    # 투표 진행 바
    bar_x, bar_y, bar_w, bar_h = 10, fh - 20, fw - 20, 12
    cv2.rectangle(disp, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (60, 60, 60), -1)
    if total > 0:
        fill = int(bar_w * total / _MAX_CAPTURE)
        vote_ratio = votes / total
        bar_color = (0, 200, 0) if vote_ratio >= _VOTE_RATIO_MIN else (0, 100, 255)
        cv2.rectangle(disp, (bar_x, bar_y), (bar_x + fill, bar_y + bar_h), bar_color, -1)
    cv2.rectangle(disp, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (120, 120, 120), 1)

    return disp


def _draw_done(frame, passed: bool, votes: int, total: int, avg_score: float):
    disp = frame.copy()
    fh, fw = disp.shape[:2]

    # 전체 반투명 오버레이
    overlay = disp.copy()
    tint = (10, 40, 10) if passed else (40, 10, 10)
    cv2.rectangle(overlay, (0, 0), (fw, fh), tint, -1)
    cv2.addWeighted(overlay, 0.45, disp, 0.55, 0, disp)

    ratio = votes / total if total else 0
    result_text  = "SUCCESS" if passed else "FAIL"
    result_color = (60, 230, 60) if passed else (60, 60, 230)

    # 결과 텍스트
    (tw, th), _ = cv2.getTextSize(result_text, cv2.FONT_HERSHEY_DUPLEX, 2.8, 4)
    rx = (fw - tw) // 2
    ry = fh // 2 - 20
    cv2.putText(disp, result_text, (rx, ry), cv2.FONT_HERSHEY_DUPLEX, 2.8, (0, 0, 0), 7)
    cv2.putText(disp, result_text, (rx, ry), cv2.FONT_HERSHEY_DUPLEX, 2.8, result_color, 4)

    # 세부 정보
    lines = [
        f"Votes: {votes}/{total}  ({ratio:.0%})",
        f"Avg Score: {avg_score:.4f}   Threshold: {FACE_MATCH_THRESHOLD}",
        "R : Retry    Q : Quit",
    ]
    for i, line in enumerate(lines):
        y_pos = ry + 50 + i * 34
        _put_text_shadow(disp, line, (fw // 2 - 160, y_pos), 0.72, (220, 220, 220))

    return disp


# ── 메인 ─────────────────────────────────────────────────────────────────────

def run_test():
    from face_detection.mediapipe_detector import detect_face

    print("=" * 55)
    print("  얼굴 인증 단독 테스트")
    print(f"  임계값: {FACE_MATCH_THRESHOLD}   투표 비율: {_VOTE_RATIO_MIN}")
    print(f"  캡처: {_MAX_CAPTURE}프레임 / 타임아웃: {_TIMEOUT_SEC}s")
    print("  1: 시작   R: 재시작   Q: 종료")
    print("=" * 55)

    embeddings = _load_embeddings()
    if not embeddings:
        print("[ERROR] 저장된 임베딩 없음 — 먼저 얼굴 등록을 진행해주세요.")
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] 카메라를 열 수 없습니다.")
        return

    print("[CAM] 카메라 워밍업 중...")
    time.sleep(1.0)

    def new_state():
        return {
            "phase":        _STATE_STANDBY,
            "face_imgs":    [],
            "scores":       [],
            "votes":        0,
            "start_time":   None,
            "last_capture": 0.0,
            "result":       None,
        }

    s = new_state()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.02)
                continue

            fh, fw = frame.shape[:2]
            now = time.time()

            face_detected = None
            centered      = False
            last_score    = None

            # ── 대기 ──────────────────────────────────────────────────────────
            if s["phase"] == _STATE_STANDBY:
                # 미리 카메라는 보여 주되 감지/임베딩은 하지 않음
                disp = _draw_standby(frame, len(embeddings))

            # ── 진행 중 ───────────────────────────────────────────────────────
            elif s["phase"] == _STATE_RUNNING:
                if s["start_time"] is None:
                    s["start_time"] = now

                elapsed   = now - s["start_time"]
                remaining = max(0.0, _TIMEOUT_SEC - elapsed)
                total     = len(s["face_imgs"])

                small = cv2.resize(frame, (320, 240))
                faces = detect_face(small)

                if faces:
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
                    face_detected = (x, y, w, h)
                    centered = _is_centered(face_detected, fw)

                    if centered and now - s["last_capture"] >= _CAPTURE_INTERVAL:
                        crop = _crop_face(frame, face_detected, fh, fw)
                        if crop is not None:
                            try:
                                emb = _get_embedding(crop)
                                best_score = max(
                                    _cosine_similarity(emb, ref)
                                    for ref in embeddings.values()
                                )
                                last_score = best_score
                                s["face_imgs"].append(crop)
                                s["scores"].append(best_score)
                                if best_score >= FACE_MATCH_THRESHOLD:
                                    s["votes"] += 1
                                s["last_capture"] = now
                                total = len(s["face_imgs"])

                                print(
                                    f"[{total:02d}/{_MAX_CAPTURE}] "
                                    f"score={best_score:.4f}  "
                                    f"votes={s['votes']}/{total}"
                                )
                            except Exception as e:
                                print(f"[EMBED ERR] {e}")

                # 판정 조건 체크
                finished = total >= _MAX_CAPTURE or (elapsed >= _TIMEOUT_SEC and total > 0)
                timed_out_no_face = elapsed >= _TIMEOUT_SEC and total == 0

                if finished or timed_out_no_face:
                    ratio  = s["votes"] / total if total else 0
                    passed = ratio >= _VOTE_RATIO_MIN and total > 0
                    s["phase"]  = _STATE_DONE
                    s["result"] = passed
                    avg = float(np.mean(s["scores"])) if s["scores"] else 0.0
                    label = "SUCCESS" if passed else "FAIL"
                    print()
                    print("=" * 45)
                    print(f"  판정: {label}")
                    print(f"  프레임: {total}   투표: {s['votes']}   비율: {ratio:.2%}")
                    print(f"  평균 유사도: {avg:.4f}   임계값: {FACE_MATCH_THRESHOLD}")
                    print("=" * 45)
                    print("R: 재시작   Q: 종료\n")

                disp = _draw_running(frame, face_detected, centered, last_score,
                                     s["votes"], len(s["face_imgs"]), remaining)

            # ── 완료 ──────────────────────────────────────────────────────────
            else:
                total    = len(s["face_imgs"])
                avg      = float(np.mean(s["scores"])) if s["scores"] else 0.0
                disp = _draw_done(frame, s["result"], s["votes"], total, avg)

            cv2.imshow("Face Auth Test", disp)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("1") and s["phase"] == _STATE_STANDBY:
                print("\n[START] 인증 시작\n")
                s = new_state()
                s["phase"] = _STATE_RUNNING
            elif key == ord("r") and s["phase"] == _STATE_DONE:
                print("\n[RESET] 재시작\n")
                s = new_state()

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[CAM] 종료")


if __name__ == "__main__":
    run_test()
