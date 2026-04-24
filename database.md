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
| `devices` | 디스펜서 기기 |
| `face_embeddings` | 얼굴 벡터 (pgvector) |
| `notifications` | 알림 이력 |

---

## 관계도

```
members ──< patients ──< schedules >── medications
                │            │
                │            └──< activities >── notifications
                │                                      │
                ├──< devices                    members ┘
                │
                └──< face_embeddings
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
디스펜서 기기. `device_uid`로 식별.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `device_id` | serial4 | PK | 자동 증가 ID |
| `device_uid` | varchar(100) | ✓ | 기기 고유 식별자 (UUID 등) |
| `patient_id` | int4 | | 환자 FK → `patients.patient_id` (null = 미등록) |
| `device_name` | varchar(100) | ✓ | 기기 이름 (default: `UNKNOWN`) |
| `device_status` | varchar(50) | | 기기 상태 (default: `UNREGISTERED`) |
| `last_ping` | timestamptz | | 마지막 통신 시각 |
| `registered_at` | timestamptz | ✓ | 등록일시 |

**인덱스**
- `ix_devices_1` — `registered_at` B-tree

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
