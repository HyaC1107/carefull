# 안내 음성 스크립트

저장 위치: `raspberry/assets/voices/`  
포맷: MP3 (pygame.mixer 재생)  
대상: 고령자 → 천천히, 명확하게, 친근한 톤

---

## 1. 사용자 등록 플로우

### 1-1. 등록 안내 화면 (`register.py` 진입 시)

| 파일명 | 대사 |
|---|---|
| `reg_start.mp3` | "사용자 등록을 시작합니다. 얼굴 촬영 후 지문 등록 순서로 진행됩니다." |

---

### 1-2. 얼굴 촬영 (`camera_view.py` — 등록 모드)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `reg_face_guide.mp3` | 카메라 준비 완료 직후 | "카메라를 바라봐 주세요. 자동으로 촬영됩니다." |
| `reg_face_front.mp3` | 정면 방향 전환 | "정면을 바라봐 주세요." |
| `reg_face_up.mp3` | 위 방향 전환 | "위를 바라봐 주세요." |
| `reg_face_down.mp3` | 아래 방향 전환 | "아래를 바라봐 주세요." |
| `reg_face_left.mp3` | 왼쪽 방향 전환 | "왼쪽을 바라봐 주세요." |
| `reg_face_right.mp3` | 오른쪽 방향 전환 | "오른쪽을 바라봐 주세요." |
| `reg_face_done.mp3` | 20장 촬영 완료 | "얼굴 촬영이 완료되었습니다." |

---

### 1-3. 지문 등록 (`fingerprint_register.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `reg_fp_start.mp3` | 화면 진입 시 | "지문 등록을 시작합니다. 센서에 손가락을 올려주세요." |
| `reg_fp_lift.mp3` | 1차 스캔 완료 (`손가락 떼주세요` 단계) | "손가락을 떼주세요." |
| `reg_fp_again.mp3` | 2차 스캔 요청 (`다시 올려주세요` 단계) | "다시 한번 올려주세요." |
| `reg_fp_done.mp3` | 손가락 1개 등록 완료 | "등록이 완료되었습니다." |
| `reg_fp_more.mp3` | 추가 등록 프롬프트 표시 시 | "다른 손가락도 등록하시겠습니까?" |
| `reg_fp_error.mp3` | 등록 오류 발생 시 | "인식에 실패했습니다. 다시 시도해 주세요." |

---

### 1-4. 등록 완료

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `reg_complete.mp3` | 등록 완료 화면 진입 시 | "사용자 등록이 완료되었습니다. 이제 복약 관리를 시작할 수 있습니다." |

---

## 2. 복약 프로세스 플로우

### 2-1. 복약 알림 (`medication_start.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_alarm.mp3` | 화면 진입 시 (알람과 함께) | "약 드실 시간입니다. 카메라 앞에 서주시면 자동으로 시작됩니다." |

---

### 2-2. 얼굴 인증 (`camera_view.py` — 인증 모드)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_auth_face.mp3` | 카메라 준비 완료 직후 | "얼굴 인증을 진행합니다. 카메라를 바라봐 주세요." |

---

### 2-3. 지문 인증 폴백 (`fingerprint_auth.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_auth_fp.mp3` | 화면 진입 시 | "지문 인증을 진행합니다. 센서에 손가락을 올려주세요." |
| `med_auth_fp_retry.mp3` | 인식 실패 후 재시도 버튼 표시 시 | "인식하지 못했습니다. 다시 올려주세요." |

---

### 2-4. 인증 결과 (`auth_result.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_auth_success.mp3` | 인증 성공 시 | "인증이 완료되었습니다. 약을 준비하고 있습니다." |
| `med_auth_fail.mp3` | 인증 최종 실패 시 | "인증에 실패하였습니다. 처음 화면으로 돌아갑니다." |

---

### 2-5. 약 배출 (`dispensing.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_dispensing.mp3` | 화면 진입 시 | "약이 나오고 있습니다. 잠시 기다려 주세요." |

---

### 2-6. 복약 (`medication.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_take.mp3` | 화면 진입 시 | "약을 꺼내서 물과 함께 드세요." |

---

### 2-7. 복약 완료 (`complete.py`)

| 파일명 | 발생 시점 | 대사 |
|---|---|---|
| `med_complete.mp3` | 화면 진입 시 | "복약이 완료되었습니다. 수고하셨습니다." |

---

## 파일 목록 요약

```
raspberry/assets/voices/
│
├── [등록 플로우]
│   ├── reg_start.mp3
│   ├── reg_face_guide.mp3
│   ├── reg_face_front.mp3
│   ├── reg_face_up.mp3
│   ├── reg_face_down.mp3
│   ├── reg_face_left.mp3
│   ├── reg_face_right.mp3
│   ├── reg_face_done.mp3
│   ├── reg_fp_start.mp3
│   ├── reg_fp_lift.mp3
│   ├── reg_fp_again.mp3
│   ├── reg_fp_done.mp3
│   ├── reg_fp_more.mp3
│   ├── reg_fp_error.mp3
│   └── reg_complete.mp3
│
└── [복약 플로우]
    ├── med_alarm.mp3
    ├── med_auth_face.mp3
    ├── med_auth_fp.mp3
    ├── med_auth_fp_retry.mp3
    ├── med_auth_success.mp3
    ├── med_auth_fail.mp3
    ├── med_dispensing.mp3
    ├── med_take.mp3
    └── med_complete.mp3
```

---

## 제작 가이드

- **속도**: 일반 TTS보다 10~15% 느리게 (고령자 대상)
- **톤**: 부드럽고 친근한 여성 또는 중성 목소리
- **포맷**: MP3, 44.1kHz, 128kbps 이상
- **무음 여백**: 앞뒤 0.2초 내외 (pygame 재생 시 즉시 재생 위해 앞 여백 최소화)
- **기존 알람음과 중복 방지**: `med_alarm.mp3`는 `alarm.mp3`(벨소리)와 별개 파일로 관리
