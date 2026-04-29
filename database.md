# Carefull — Database Schema

PostgreSQL + pgvector 확장 사용.

## 테이블 목록

| 테이블 | 설명 |
|---|---|
| `medications` | 약 사전 (식약처 기준) |
| `members` | 보호자 계정 (소셜 로그인) |
| `patients` | 환자 정보 |
| `schedules` | 복약 스케줄 |
| `activities` | 복약 로그 |
| `devices` | 디스펜서 기기 (알림음 파일 포함) |
| `face_embeddings` | 얼굴 벡터 (pgvector) |
| `fingerprints` | 지문 슬롯 (R307 센서) |
| `voice_samples` | 보호자 목소리 파일 |
| `notifications` | FCM 알림 이력 |
| `push_tokens` | FCM 푸시 토큰 |

---

## 관계도

```
members ──< patients ──< schedules >── medications
   │            │            │
   │            │            └──< activities >── notifications
   │            │                                      │
   │            ├──< devices                    members ┘
   │            ├──< face_embeddings
   │            ├──< fingerprints
   │            └──< voice_samples
   │
   └──< push_tokens
```

---

## 테이블 상세

### medications
약 사전. 식약처 기준 약품 정보.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `medi_id` | serial4 | PK | 자동 증가 ID |
| `item_seq` | varchar(50) | | 식약처 품목 일련번호 (Unique) |
| `medi_name` | varchar(255) | ✓ | 약품명 |
| `medi_class` | varchar(100) | | 약품 분류 |

**인덱스**
- `idx_medi_name_trgm` — GIN (trigram) 인덱스 → 약품명 부분 검색 최적화

---

### members
보호자 계정. 소셜 로그인(카카오/네이버/구글) 기반.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `mem_id` | serial4 | PK | 자동 증가 ID |
| `social_id` | varchar(100) | ✓ | 소셜 제공자 고유 ID |
| `provider` | varchar(20) | ✓ | 소셜 제공자 (`kakao` / `naver` / `google`) |
| `email` | varchar(100) | ✓ | 이메일 |
| `nick` | varchar(50) | ✓ | 닉네임 |
| `profile_img` | text | ✓ | 프로필 이미지 URL |
| `joined_at` | timestamptz | ✓ | 가입일시 (default: now) |

**인덱스**
- `ix_members_1` — `joined_at` B-tree
- `uq_members_1` — `(email, nick)` Unique

---

### patients
환자 정보. 보호자(`members`)에 종속.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `patient_id` | serial4 | PK | 자동 증가 ID |
| `mem_id` | int4 | ✓ | 보호자 FK → `members.mem_id` |
| `patient_name` | varchar(100) | | 환자 이름 |
| `birthdate` | date | ✓ | 생년월일 |
| `gender` | char(1) | ✓ | 성별 (`M` / `F`) |
| `phone` | varchar(20) | ✓ | 전화번호 |
| `address` | varchar(255) | ✓ | 주소 |
| `bloodtype` | varchar(5) | ✓ | 혈액형 |
| `height` | numeric(5,2) | ✓ | 키 (cm) |
| `weight` | numeric(5,2) | ✓ | 몸무게 (kg) |
| `fingerprint_id` | int4 | ✓ | R307 지문 센서 내부 ID |
| `guardian_name` | varchar(100) | ✓ | 긴급 연락처 이름 |
| `guardian_phone` | varchar(20) | ✓ | 긴급 연락처 전화번호 |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `updated_at` | timestamptz | | 수정일시 |
| `deleted_at` | timestamptz | | 삭제일시 (소프트 삭제) |

---

### schedules
복약 스케줄. 환자별 약/시간 정의.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `sche_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `medi_id` | int4 | ✓ | 약품 FK → `medications.medi_id` |
| `start_date` | date | ✓ | 복약 시작일 |
| `end_date` | date | | 복약 종료일 (null = 무기한) |
| `time_to_take` | time | ✓ | 복약 시각 (HH:MM:SS) |
| `dose_interval` | int4 | | 복약 간격 (분) |
| `status` | varchar(20) | ✓ | 스케줄 상태 (`ACTIVE` / `INACTIVE` 등) |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `updated_at` | timestamptz | | 수정일시 |

**인덱스**
- `ix_schedules_1` — `created_at` B-tree

---

### activities
복약 로그. 스케줄 1회 실행 결과.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `activity_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `sche_id` | int4 | ✓ | 스케줄 FK → `schedules.sche_id` |
| `sche_time` | timestamptz | ✓ | 예정 복약 시각 |
| `actual_time` | timestamptz | | 실제 복약 시각 (null = 미복용) |
| `status` | varchar(20) | ✓ | 결과 상태 (`TAKEN` / `MISSED` / `PENDING` 등) |
| `is_face_auth` | bool | ✓ | 얼굴 인증 성공 여부 |
| `is_ai_check` | bool | ✓ | AI 행동 인식 성공 여부 |
| `similarity_score` | numeric(5,4) | ✓ | 얼굴 유사도 점수 (0.0000~1.0000) |
| `created_at` | timestamptz | ✓ | 생성일시 |

**인덱스**
- `ix_activities_1` — `created_at` B-tree
- `ix_activities_2` — `(patient_id, sche_time)` B-tree → 환자별 시간순 조회 최적화

---

### devices
디스펜서 기기. `device_uid`로 식별. 알림음 파일 경로 포함.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `device_id` | serial4 | PK | 자동 증가 ID |
| `device_uid` | varchar(100) | ✓ | 기기 고유 식별자 (UUID 등) |
| `patient_id` | int4 | | 환자 FK → `patients.patient_id` (null = 미등록) |
| `device_name` | varchar(100) | ✓ | 기기 이름 (default: `UNKNOWN`) |
| `device_status` | varchar(50) | | 기기 상태 (default: `UNREGISTERED`) |
| `last_ping` | timestamptz | | 마지막 통신 시각 |
| `registered_at` | timestamptz | ✓ | 등록일시 |
| `alarm_sound_path` | text | | 알림음 파일 상대 경로 (`uploads/sounds/...`) |
| `alarm_sound_name` | text | | 알림음 원본 파일명 |
| `alarm_sound_updated_at` | timestamptz | | 알림음 최종 업데이트 시각 |

**인덱스**
- `ix_devices_1` — `registered_at` B-tree

**마이그레이션** (미실행 시 실행 필요)
```sql
ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS alarm_sound_path TEXT,
  ADD COLUMN IF NOT EXISTS alarm_sound_name TEXT,
  ADD COLUMN IF NOT EXISTS alarm_sound_updated_at TIMESTAMPTZ;
```

---

### face_embeddings
얼굴 벡터. pgvector 확장으로 코사인 유사도 검색.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `face_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `face_vector` | vector | ✓ | 얼굴 임베딩 벡터 (MobileFaceNet 출력) |
| `created_at` | timestamptz | ✓ | 생성일시 |

**인덱스**
- `ix_face_embeddings_1` — `created_at` B-tree
- `ix_face_embeddings_2` — `face_vector` B-tree
- `ix_face_embeddings_3` — `patient_id` B-tree

---

### fingerprints
지문 슬롯. R307 지문 센서에 등록된 슬롯 정보.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `fp_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `slot_id` | int4 | ✓ | R307 센서 내부 슬롯 번호 |
| `label` | varchar | | 슬롯 이름 (default: `지문`) |
| `registered_at` | timestamptz | ✓ | 등록일시 (default: now) |

**제약**
- `(patient_id, slot_id)` Unique — 환자당 슬롯 번호 중복 불가

---

### voice_samples
보호자 목소리 파일. AI 처리 후 복약 알림 TTS에 사용.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `voice_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `file_name` | text | ✓ | 원본 파일명 |
| `file_path` | text | ✓ | 서버 저장 경로 (`uploads/voices/...`) |
| `file_size` | int8 | | 파일 크기 (bytes) |
| `mime_type` | varchar(100) | | MIME 타입 (`audio/webm` 등) |
| `status` | varchar(20) | ✓ | 처리 상태 (`pending` / `processing` / `ready` / `error`) |
| `uploaded_at` | timestamptz | ✓ | 업로드 일시 (default: now) |
| `updated_at` | timestamptz | | 상태 변경 일시 |

---

### notifications
FCM 푸시 알림 이력. 미복용 30분 초과 시 보호자 알림.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `noti_id` | serial4 | PK | 자동 증가 ID |
| `mem_id` | int4 | ✓ | 보호자 FK → `members.mem_id` |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `activity_id` | int4 | ✓ | 복약 로그 FK → `activities.activity_id` |
| `noti_type` | varchar(50) | ✓ | 알림 유형 (`MISSED` / `TAKEN` 등) |
| `noti_title` | varchar(255) | ✓ | 알림 제목 |
| `noti_msg` | text | ✓ | 알림 본문 |
| `is_received` | bool | ✓ | FCM 수신 여부 |
| `received_time` | timestamptz | | FCM 수신 시각 |
| `created_at` | timestamptz | ✓ | 생성일시 |

**인덱스**
- `ix_notifications_1` — `created_at` B-tree
- `ix_notifications_2` — `(mem_id, is_received)` B-tree → 보호자별 미확인 알림 조회 최적화

---

### push_tokens
FCM 푸시 토큰. 보호자 기기별 토큰 관리.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `push_token_id` | serial4 | PK | 자동 증가 ID |
| `mem_id` | int4 | ✓ | 보호자 FK → `members.mem_id` |
| `fcm_token` | text | ✓ | FCM 등록 토큰 (Unique) |
| `device_type` | varchar(20) | ✓ | 기기 유형 (default: `web`) |
| `is_active` | bool | ✓ | 활성 여부 (default: `true`) |
| `created_at` | timestamptz | ✓ | 생성일시 (default: now) |
| `updated_at` | timestamptz | ✓ | 수정일시 (default: now, 트리거로 자동 갱신) |

**인덱스**
- `ix_push_tokens_mem_id_is_active` — `(mem_id, is_active)` B-tree → 보호자별 활성 토큰 조회 최적화
- `uq_push_tokens_fcm_token` — `fcm_token` Unique

**트리거**
- `trg_push_tokens_updated_at` — UPDATE 시 `updated_at` 자동 갱신
