"""
복약행위 감지 파라미터 튜닝 도구
-----------------------------------
실행:  python tests/test_mp_pose.py
종료:  q 키

화면에 표시되는 정보:
  - 코/입 기준 손목 거리 (실시간)
  - 현재 카운터 / 목표 프레임 수
  - 임계값 초과 여부 (빨강/초록)

키 조작:
  + / -       임계값  +0.01 / -0.01
  ] / [       연속 프레임 수  +1 / -1
  m           기준 랜드마크 토글 (코 ↔ 입)
  r           카운터 리셋
  s           현재 설정을 behavior_thread.py 에 저장
  q           종료

로그:  logs/tune_pose_log.csv  (프레임마다 자동 기록)
"""

import csv
import datetime
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cv2
import mediapipe as mp
import numpy as np

_LOG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "logs", "tune_pose_log.csv")
)

# ── 초기 파라미터 (behavior_thread.py 와 동일하게 시작) ──────────────
DIST_THRESHOLD  = 0.3
SUCCESS_FRAMES  = 4
USE_MOUTH       = False   # False=코(0), True=입 중앙((9+10)/2)

# MediaPipe landmark 인덱스
_NOSE       = 0
_MOUTH_L    = 9
_MOUTH_R    = 10
_L_WRIST    = 15
_R_WRIST    = 16

mp_pose     = mp.solutions.pose
mp_drawing  = mp.solutions.drawing_utils


def get_ref_point(lm, use_mouth: bool):
    if use_mouth:
        mx = (lm[_MOUTH_L].x + lm[_MOUTH_R].x) / 2
        my = (lm[_MOUTH_L].y + lm[_MOUTH_R].y) / 2
        return mx, my
    return lm[_NOSE].x, lm[_NOSE].y


def draw_text(img, text, pos, color=(255, 255, 255), scale=0.7, thickness=2):
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
    cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def run():
    global DIST_THRESHOLD, SUCCESS_FRAMES, USE_MOUTH

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] 카메라를 열 수 없습니다.")
        return

    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    counter     = 0
    detected    = False
    dist_l      = -1.0
    dist_r      = -1.0
    frame_no    = 0
    session_ts  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # CSV 로그 파일 준비
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    write_header = not os.path.exists(_LOG_PATH)
    log_file = open(_LOG_PATH, "a", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)
    if write_header:
        log_writer.writerow([
            "session_time", "frame_no",
            "ref_point", "threshold", "success_frames",
            "dist_left", "dist_right", "min_dist",
            "is_near", "counter", "detected",
        ])

    print("=== 복약행위 감지 튜닝 도구 ===")
    print(f"로그 저장 경로: {_LOG_PATH}")
    print("+/-: 임계값 조정  |  ]/[: 프레임수 조정  |  m: 기준점 전환  |  r: 리셋  |  s: 저장  |  q: 종료")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        fh, fw = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        is_near = False

        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=3),
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 200, 200), thickness=1),
            )

            lm = results.pose_landmarks.landmark
            rx, ry = get_ref_point(lm, USE_MOUTH)

            dist_l = float(np.hypot(lm[_L_WRIST].x - rx, lm[_L_WRIST].y - ry))
            dist_r = float(np.hypot(lm[_R_WRIST].x - rx, lm[_R_WRIST].y - ry))
            min_d  = min(dist_l, dist_r)

            if min_d < DIST_THRESHOLD:
                is_near = True

            # 기준점 표시
            ref_px = (int(rx * fw), int(ry * fh))
            cv2.circle(frame, ref_px, 10, (0, 255, 255), -1)

            # 손목 → 기준점 라인
            lw_px = (int(lm[_L_WRIST].x * fw), int(lm[_L_WRIST].y * fh))
            rw_px = (int(lm[_R_WRIST].x * fw), int(lm[_R_WRIST].y * fh))
            l_col = (0, 80, 255) if dist_l < DIST_THRESHOLD else (180, 180, 180)
            r_col = (0, 80, 255) if dist_r < DIST_THRESHOLD else (180, 180, 180)
            cv2.line(frame, ref_px, lw_px, l_col, 2)
            cv2.line(frame, ref_px, rw_px, r_col, 2)

        # 카운터 업데이트
        if is_near:
            counter += 1
        else:
            counter = max(0, counter - 1)

        if counter >= SUCCESS_FRAMES and not detected:
            detected = True
            print(f"[DETECTED] 임계값={DIST_THRESHOLD:.2f}  프레임={SUCCESS_FRAMES}  dist_l={dist_l:.4f}  dist_r={dist_r:.4f}")

        # 프레임 로그 기록
        frame_no += 1
        min_d_log = round(min(dist_l, dist_r), 4) if dist_l >= 0 else -1.0
        log_writer.writerow([
            session_ts, frame_no,
            "mouth" if USE_MOUTH else "nose",
            DIST_THRESHOLD, SUCCESS_FRAMES,
            round(dist_l, 4), round(dist_r, 4), min_d_log,
            1 if is_near else 0, counter, 1 if detected else 0,
        ])
        log_file.flush()

        # ── 오버레이 UI ──────────────────────────────────────────────────
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (fw, 130), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        ref_label = "입(Mouth)" if USE_MOUTH else "코(Nose)"
        draw_text(frame, f"기준점: {ref_label}  [m]", (10, 28), (200, 200, 50))

        th_col = (100, 255, 100)
        draw_text(frame, f"임계값(TH): {DIST_THRESHOLD:.2f}  [↑/↓]", (10, 58), th_col)
        draw_text(frame, f"연속프레임: {SUCCESS_FRAMES}  []/[]", (10, 88), (100, 200, 255))

        # 거리 표시
        l_col_txt = (0, 80, 255) if dist_l != -1 and dist_l < DIST_THRESHOLD else (200, 200, 200)
        r_col_txt = (0, 80, 255) if dist_r != -1 and dist_r < DIST_THRESHOLD else (200, 200, 200)
        draw_text(frame, f"L:{dist_l:.3f}", (fw - 310, 28), l_col_txt)
        draw_text(frame, f"R:{dist_r:.3f}", (fw - 160, 28), r_col_txt)

        min_d_now = min(dist_l, dist_r) if dist_l >= 0 else -1.0
        draw_text(frame, f"min:{min_d_now:.3f}", (fw - 240, 58), (255, 200, 0))

        # 카운터 바
        bar_w = int((counter / max(SUCCESS_FRAMES, 1)) * (fw - 20))
        bar_w = min(bar_w, fw - 20)
        bar_col = (0, 255, 80) if detected else (0, 180, 255)
        cv2.rectangle(frame, (10, 100), (10 + bar_w, 122), bar_col, -1)
        cv2.rectangle(frame, (10, 100), (fw - 10, 122), (100, 100, 100), 1)
        draw_text(frame, f"counter: {counter}/{SUCCESS_FRAMES}", (12, 119), (255, 255, 255), 0.55, 1)

        if detected:
            cv2.rectangle(frame, (0, 0), (fw, fh), (0, 255, 0), 6)
            draw_text(frame, "DETECTED!", (fw // 2 - 100, fh // 2), (0, 255, 0), 2.0, 3)

        cv2.imshow("복약행위 튜닝 [q=종료]", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            counter  = 0
            detected = False
            print("[RESET]")
        elif key == 82 or key == ord('w'):   # ↑ 또는 w
            DIST_THRESHOLD = round(min(DIST_THRESHOLD + 0.01, 0.99), 2)
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == 84 or key == ord('s') and False:  # ↓ (s는 저장에 쓰므로 구분)
            DIST_THRESHOLD = round(max(DIST_THRESHOLD - 0.01, 0.05), 2)
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == 0:   # ↑ 화살표 (일부 터미널)
            DIST_THRESHOLD = round(min(DIST_THRESHOLD + 0.01, 0.99), 2)
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == 1:   # ↓ 화살표
            DIST_THRESHOLD = round(max(DIST_THRESHOLD - 0.01, 0.05), 2)
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == ord('+') or key == ord('='):
            DIST_THRESHOLD = round(min(DIST_THRESHOLD + 0.01, 0.99), 2)
            counter  = 0; detected = False
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == ord('-'):
            DIST_THRESHOLD = round(max(DIST_THRESHOLD - 0.01, 0.05), 2)
            counter  = 0; detected = False
            print(f"[TH] → {DIST_THRESHOLD:.2f}")
        elif key == ord(']'):
            SUCCESS_FRAMES = min(SUCCESS_FRAMES + 1, 30)
            counter = 0; detected = False
            print(f"[FRAMES] → {SUCCESS_FRAMES}")
        elif key == ord('['):
            SUCCESS_FRAMES = max(SUCCESS_FRAMES - 1, 1)
            counter = 0; detected = False
            print(f"[FRAMES] → {SUCCESS_FRAMES}")
        elif key == ord('m'):
            USE_MOUTH = not USE_MOUTH
            counter = 0; detected = False
            print(f"[REF] → {'입(Mouth)' if USE_MOUTH else '코(Nose)'}")
        elif key == ord('s'):
            _save_to_behavior_thread(DIST_THRESHOLD, SUCCESS_FRAMES)

    cap.release()
    pose.close()
    cv2.destroyAllWindows()
    log_file.close()
    print(f"\n최종 설정 — 임계값: {DIST_THRESHOLD:.2f}  연속프레임: {SUCCESS_FRAMES}  기준점: {'입' if USE_MOUTH else '코'}")
    print(f"로그 저장됨: {_LOG_PATH}")


def _save_to_behavior_thread(threshold: float, frames: int):
    """s 키 → behavior_thread.py 의 상수를 실제로 덮어씁니다."""
    target = os.path.join(os.path.dirname(__file__), "..", "ui", "threads", "behavior_thread.py")
    target = os.path.normpath(target)
    try:
        with open(target, "r", encoding="utf-8") as f:
            src = f.read()

        import re
        src = re.sub(
            r"(_DIST_THRESHOLD\s*=\s*)[\d.]+",
            lambda m: f"{m.group(1)}{threshold}",
            src,
        )
        src = re.sub(
            r"(_SUCCESS_FRAMES\s*=\s*)\d+",
            lambda m: f"{m.group(1)}{frames}",
            src,
        )

        with open(target, "w", encoding="utf-8") as f:
            f.write(src)

        print(f"[SAVED] behavior_thread.py 업데이트 → TH={threshold:.2f}  FRAMES={frames}")
    except Exception as e:
        print(f"[SAVE ERROR] {e}")


if __name__ == "__main__":
    run()
