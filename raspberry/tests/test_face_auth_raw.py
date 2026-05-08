"""
얼굴 인증 로직 독립 디버그 테스트
서비스(camera_view.py + _AuthWorker)와 동일한 배치 캡처 + 다수결 로직을 cv2 창으로 실행.

실행: python tests/test_face_auth_raw.py   (raspberry/ 루트에서)
조작: Q=종료   R=재시작(수집 초기화)
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2

# ── 서비스와 동일한 파라미터 ────────────────────────────────────────
MAX_CAPTURE      = 15
CAPTURE_INTERVAL = 0.13   # 초
AUTH_TIMEOUT     = 7.0    # 초
CENTER_TOL       = 0.15   # 수평 ±15%
STRICT_RATIO     = 0.6    # 다수결 승인 임계값
FACE_SCALE       = 2      # 320→640 좌표 복원 배율

_WIN = "Face Auth Debug"


def _is_centered(face, fw: int) -> bool:
    x, y, w, h = face
    return abs((x + w / 2) - fw / 2) < fw * CENTER_TOL


def _majority_vote(face_imgs: list):
    """서비스 _AuthWorker와 동일한 다수결 로직."""
    from auth.authenticate import authenticate

    results: dict = {}
    total = len(face_imgs)

    for i, img in enumerate(face_imgs):
        user, score = authenticate(img)
        label = "✓" if user else "✗"
        print(f"  [{i+1:2d}/{total}] {label}  user={user}  score={score:.4f}")
        if user:
            results.setdefault(user, []).append(score)

    if not results:
        return None, 0.0, 0.0

    best_user, max_votes, best_avg = None, 0, 0.0
    for user, scores in results.items():
        votes = len(scores)
        avg = sum(scores) / votes
        if votes > max_votes or (votes == max_votes and avg > best_avg):
            best_user, max_votes, best_avg = user, votes, avg

    ratio = max_votes / total
    return best_user, best_avg, ratio


def _reset_state():
    return {
        "face_imgs": [],
        "last_cap":  0.0,
        "deadline":  None,
        "phase":     "collecting",   # collecting | voting | result
        "result_text":    "",
        "result_color":   (0, 255, 0),
        "result_details": [],
    }


def main():
    from camera.camera import get_frame
    from face_detection.mediapipe_detector import detect_face

    cv2.namedWindow(_WIN, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(_WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    s = _reset_state()

    print("=" * 50)
    print("얼굴 인증 디버그 테스트 시작")
    print(f"  목표: {MAX_CAPTURE}장  타임아웃: {AUTH_TIMEOUT}s  승인기준: {STRICT_RATIO*100:.0f}%")
    print("  Q=종료  R=재시작")
    print("=" * 50)

    try:
        while True:
            frame = get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            disp = frame.copy()
            fh, fw = frame.shape[:2]
            now = time.time()

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            if key == ord('r') and s["phase"] != "voting":
                s = _reset_state()
                print("\n[RESET] 재시작")

            # ── collecting ──────────────────────────────────────────
            if s["phase"] == "collecting":
                if s["deadline"] is None:
                    s["deadline"] = now + AUTH_TIMEOUT

                remaining = max(0.0, s["deadline"] - now)

                small = cv2.resize(frame, (320, 240))
                faces = detect_face(small)

                if faces:
                    rx, ry, rw, rh = [v * FACE_SCALE for v in faces[0]]
                    centered = _is_centered((rx, ry, rw, rh), fw)
                    color = (0, 255, 0) if centered else (0, 165, 255)
                    cv2.rectangle(disp, (rx, ry), (rx + rw, ry + rh), color, 2)

                    if centered:
                        if now - s["last_cap"] > CAPTURE_INTERVAL and len(s["face_imgs"]) < MAX_CAPTURE:
                            face_bgr = frame[max(0, ry):min(fh, ry+rh), max(0, rx):min(fw, rx+rw)]
                            if face_bgr.size > 0:
                                s["face_imgs"].append(face_bgr)
                                s["last_cap"] = now
                                print(f"[CAPTURE] {len(s['face_imgs'])}/{MAX_CAPTURE}")
                    else:
                        cv2.putText(disp, "중앙으로 이동하세요", (fw // 2 - 140, 50),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 165, 255), 2)

                # 진행바 + 상태 텍스트
                cv2.putText(disp, f"Captured: {len(s['face_imgs'])}/{MAX_CAPTURE}",
                            (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                cv2.putText(disp, f"Timeout: {remaining:.1f}s",
                            (10, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                bar_w = int((len(s["face_imgs"]) / MAX_CAPTURE) * (fw - 20))
                cv2.rectangle(disp, (10, fh - 30), (fw - 10, fh - 10), (50, 50, 50), -1)
                cv2.rectangle(disp, (10, fh - 30), (10 + bar_w, fh - 10), (0, 200, 0), -1)

                # 전환 조건
                if len(s["face_imgs"]) >= MAX_CAPTURE:
                    s["phase"] = "voting"
                    print(f"\n[VOTING] {len(s['face_imgs'])}장 수집 완료 → 다수결 판정")
                elif now > s["deadline"]:
                    if s["face_imgs"]:
                        s["phase"] = "voting"
                        print(f"\n[VOTING] 타임아웃, {len(s['face_imgs'])}장으로 판정")
                    else:
                        s["phase"] = "result"
                        s["result_text"] = "FAILED - 얼굴 미감지"
                        s["result_color"] = (0, 0, 255)
                        s["result_details"] = ["카메라 앞에 얼굴이 없었습니다"]
                        print("[RESULT] 타임아웃 - 얼굴 없음")

            # ── voting ──────────────────────────────────────────────
            elif s["phase"] == "voting":
                cv2.putText(disp, "분석 중...", (fw // 2 - 80, fh // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 0), 3)
                cv2.imshow(_WIN, disp)
                cv2.waitKey(1)

                user, avg_score, ratio = _majority_vote(s["face_imgs"])
                total = len(s["face_imgs"])

                if user and ratio >= STRICT_RATIO:
                    s["result_text"] = f"SUCCESS: {user}"
                    s["result_color"] = (0, 220, 0)
                    s["result_details"] = [
                        f"Avg Score : {avg_score:.4f}",
                        f"Ratio     : {ratio*100:.1f}%  ({int(ratio*total)}/{total})",
                    ]
                    print(f"[RESULT] 인증 성공  user={user}  score={avg_score:.4f}  ratio={ratio*100:.1f}%")
                else:
                    s["result_text"] = "FAILED - 인증 거부"
                    s["result_color"] = (0, 0, 255)
                    if user:
                        s["result_details"] = [
                            f"Best: {user}  Avg: {avg_score:.4f}",
                            f"Ratio: {ratio*100:.1f}% < {STRICT_RATIO*100:.0f}% 기준 미달",
                        ]
                    else:
                        s["result_details"] = ["매칭되는 사용자 없음 (DB 확인 필요)"]
                    print(f"[RESULT] 인증 실패  user={user}  ratio={ratio*100:.1f}%")

                s["phase"] = "result"

            # ── result ──────────────────────────────────────────────
            elif s["phase"] == "result":
                overlay = disp.copy()
                cv2.rectangle(overlay, (0, 0), (fw, fh), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.65, disp, 0.35, 0, disp)

                cv2.putText(disp, s["result_text"],
                            (fw // 2 - 220, fh // 2 - 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.4, s["result_color"], 3)
                for i, line in enumerate(s["result_details"]):
                    cv2.putText(disp, line,
                                (fw // 2 - 220, fh // 2 + 20 + i * 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
                cv2.putText(disp, "R = 재시작    Q = 종료",
                            (fw // 2 - 140, fh - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.85, (180, 180, 180), 2)

            cv2.imshow(_WIN, disp)

    finally:
        cv2.destroyAllWindows()
        print("테스트 종료")


if __name__ == "__main__":
    main()
