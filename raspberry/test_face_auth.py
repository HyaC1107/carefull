"""
얼굴 인증 단독 테스트 스크립트
실행: raspberry/ 디렉토리에서 python test_face_auth.py

표시 정보
  - 카메라 피드 + 얼굴 박스 (초록: 중앙 정렬, 노랑: 감지됨, 빨강: 미감지)
  - 프레임별 코사인 유사도
  - 캡처 진행 (N/15) 및 투표 현황
  - 최종 판정 결과
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

# ── 설정 ──────────────────────────────────────────────────────────────────────
from config.settings import (
    CAMERA_WIDTH, CAMERA_HEIGHT, FACE_MATCH_THRESHOLD,
    DB_DIR, MODEL_PATH,
)

_FACE_MARGIN       = 0.2
_CENTER_TOL        = 0.15
_MAX_CAPTURE       = 15
_CAPTURE_INTERVAL  = 0.13   # 초
_VOTE_RATIO_MIN    = 0.45   # votes/total ≥ 0.45 → 인증 성공
_TIMEOUT_SEC       = 10     # 캡처 최대 시간

_USER_DB_PATH = os.path.join(DB_DIR, "user_db.json")

# ── 임베딩 로드 ───────────────────────────────────────────────────────────────

def _load_embeddings() -> dict:
    """로컬 user_db.json → 서버 순으로 임베딩 로드."""
    # 1) 서버
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

    # 2) 로컬 fallback
    try:
        with open(_USER_DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        result = {k: np.array(v, dtype=np.float32) for k, v in data.items()}
        print(f"[EMB] 로컬 DB에서 {len(result)}개 임베딩 로드")
        return result
    except Exception as e:
        print(f"[EMB] 로컬 DB 로드 실패: {e}")
        return {}


# ── 얼굴 감지 / 임베딩 유틸 ──────────────────────────────────────────────────

def _is_centered(face, fw: int) -> bool:
    x, y, w, h = face
    cx = x + w / 2
    return abs(cx - fw / 2) < fw * _CENTER_TOL


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
    x1 = max(0, x - mx)
    y1 = max(0, y - my)
    x2 = min(fw, x + w + mx)
    y2 = min(fh, y + h + my)
    crop = frame[y1:y2, x1:x2]
    return crop if crop.size > 0 else None


# ── 결과 오버레이 ─────────────────────────────────────────────────────────────

def _draw_overlay(frame, face, centered, score, votes, total, status_msg):
    disp = frame.copy()
    fh, fw = disp.shape[:2]

    if face is not None:
        x, y, w, h = face
        color = (0, 220, 0) if centered else (0, 200, 200)
        cv2.rectangle(disp, (x, y), (x + w, y + h), color, 2)
        if score is not None:
            cv2.putText(disp, f"{score:.3f}", (x, max(y - 8, 16)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    # 상단 정보 패널
    lines = [
        f"Threshold: {FACE_MATCH_THRESHOLD:.2f}  VoteRatio: {_VOTE_RATIO_MIN}",
        f"Captured: {total}/{_MAX_CAPTURE}   Votes: {votes}  ({votes/max(total,1)*100:.0f}%)",
        f"Status: {status_msg}",
        "Q = 종료  R = 다시 시작",
    ]
    for i, line in enumerate(lines):
        y_pos = 24 + i * 26
        cv2.putText(disp, line, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (30, 30, 30), 2)
        cv2.putText(disp, line, (10, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 220, 220), 1)

    return disp


# ── 메인 루프 ─────────────────────────────────────────────────────────────────

def run_test():
    from face_detection.mediapipe_detector import detect_face

    print("=" * 55)
    print("  얼굴 인증 단독 테스트")
    print(f"  임계값: {FACE_MATCH_THRESHOLD}  투표 비율: {_VOTE_RATIO_MIN}")
    print(f"  최대 {_MAX_CAPTURE}프레임 캡처 후 다수결 판정")
    print("  Q: 종료   R: 다시 시작")
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

    print("[CAM] 카메라 워밍업 중 (1초)...")
    time.sleep(1.0)

    def reset_state():
        return {
            "face_imgs":       [],
            "scores":          [],
            "votes":           0,
            "start_time":      None,
            "last_capture":    0.0,
            "done":            False,
            "result":          None,
            "status":          "얼굴을 카메라 정면에 위치시켜주세요",
        }

    state = reset_state()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] 프레임 읽기 실패")
                time.sleep(0.05)
                continue

            fh, fw = frame.shape[:2]
            now = time.time()

            face_detected = None
            centered      = False
            last_score    = None

            if not state["done"]:
                if state["start_time"] is None:
                    state["start_time"] = now

                elapsed = now - state["start_time"]
                remaining = max(0, _TIMEOUT_SEC - elapsed)

                small = cv2.resize(frame, (320, 240))
                faces = detect_face(small)

                if faces:
                    sx, sy, sw, sh = faces[0]
                    x, y, w, h = sx * 2, sy * 2, sw * 2, sh * 2
                    face_detected = (x, y, w, h)
                    centered = _is_centered(face_detected, fw)

                    if centered and now - state["last_capture"] >= _CAPTURE_INTERVAL:
                        crop = _crop_face(frame, face_detected, fh, fw)
                        if crop is not None:
                            try:
                                emb = _get_embedding(crop)
                                best_score = max(
                                    _cosine_similarity(emb, ref)
                                    for ref in embeddings.values()
                                )
                                last_score = best_score
                                state["face_imgs"].append(crop)
                                state["scores"].append(best_score)
                                if best_score >= FACE_MATCH_THRESHOLD:
                                    state["votes"] += 1
                                state["last_capture"] = now

                                total = len(state["face_imgs"])
                                print(
                                    f"[FRAME {total:02d}/{_MAX_CAPTURE}] "
                                    f"score={best_score:.4f}  "
                                    f"votes={state['votes']}/{total}"
                                )
                                state["status"] = (
                                    f"캡처 {total}/{_MAX_CAPTURE}  "
                                    f"유사도 {best_score:.3f}  "
                                    f"남은시간 {remaining:.1f}s"
                                )
                            except Exception as e:
                                print(f"[EMBED ERR] {e}")
                    else:
                        state["status"] = (
                            f"중앙 정렬 필요  남은시간 {remaining:.1f}s"
                            if not centered else
                            f"감지됨  남은시간 {remaining:.1f}s"
                        )
                else:
                    state["status"] = f"얼굴 미감지  남은시간 {remaining:.1f}s"

                total = len(state["face_imgs"])

                # 캡처 완료 or 타임아웃 → 판정
                if total >= _MAX_CAPTURE or (elapsed >= _TIMEOUT_SEC and total > 0):
                    ratio = state["votes"] / total if total else 0
                    passed = ratio >= _VOTE_RATIO_MIN

                    state["done"]   = True
                    state["result"] = passed
                    label = "SUCCESS" if passed else "FAIL"
                    avg_score = np.mean(state["scores"]) if state["scores"] else 0

                    print()
                    print("=" * 45)
                    print(f"  판정: {label}")
                    print(f"  프레임: {total}  투표: {state['votes']}  비율: {ratio:.2%}")
                    print(f"  평균유사도: {avg_score:.4f}  임계값: {FACE_MATCH_THRESHOLD}")
                    print("=" * 45)
                    print("R: 다시 시작   Q: 종료")

                    state["status"] = (
                        f"[인증 성공]  투표 {state['votes']}/{total} ({ratio:.0%})"
                        if passed else
                        f"[인증 실패]  투표 {state['votes']}/{total} ({ratio:.0%})"
                    )

                elif elapsed >= _TIMEOUT_SEC and total == 0:
                    state["done"]   = True
                    state["result"] = False
                    state["status"] = "[타임아웃] 얼굴을 감지하지 못했습니다"
                    print("[RESULT] 타임아웃 — 얼굴 미감지")

            # ── 오버레이 렌더링 ──────────────────────────────────────────────
            disp = _draw_overlay(
                frame, face_detected, centered,
                last_score, state["votes"], len(state["face_imgs"]),
                state["status"],
            )

            # 결과 배너
            if state["done"]:
                color = (0, 180, 0) if state["result"] else (0, 0, 200)
                text  = "SUCCESS" if state["result"] else "FAIL"
                cv2.putText(disp, text, (fw // 2 - 80, fh // 2),
                            cv2.FONT_HERSHEY_DUPLEX, 2.5, color, 4)

            cv2.imshow("Face Auth Test", disp)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("r"):
                print("\n[RESET] 다시 시작\n")
                state = reset_state()

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("[CAM] 종료")


if __name__ == "__main__":
    run_test()
