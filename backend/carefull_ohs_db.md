# Carefull — Database Schema & AI 작업 기준 (통합본)

이 문서는 `database.md`를 기준으로, `carefull_db_schema.md`의 현재 DDL 기준과 `carefull_final_db.md`의 네이밍/코드 반영 규칙을 통합한 최종 MD 파일이다.

## 문서 사용 원칙

아래 SQL은 현재 프로젝트의 DB 구조를 설명하기 위한 **문서용 DDL**이다.

AI 작업자는 이 SQL을 임의 실행하거나 마이그레이션 파일을 생성하지 않는다. DB 스키마 수정 요청이 없는 한 테이블/컬럼 추가, 삭제, 변경을 금지한다. 코드 수정 시에는 이 문서에 존재하는 테이블과 컬럼만 사용한다.

주의:
- `DROP TABLE` 문은 포함하지 않는다.
- `INSERT INTO` 데이터는 포함하지 않는다.
- 실제 DB 스키마와 다른 컬럼명을 추측해서 사용하지 않는다.
- `mem_id`, `patient_id`, `device_uid`, `sche_id`, `medi_id`, `activity_id`, `noti_id` 등 기존 키 이름을 임의 변경하지 않는다.
- 환경별 URL/도메인/포트 값은 DB 스키마와 무관하며 `.env` 기준을 유지한다.
- 전체 코드 생성/전체 파일 재작성 금지. 수정 파일 목록과 핵심 diff만 출력한다.

---

## 네이밍 기준

DB 컬럼명 / API 요청 키 / API 응답 키 / SQL alias는 기본적으로 `snake_case`를 기준으로 한다.

반드시 유지할 최종 명칭:

| 예전 명칭 | 최종 명칭 |
|---|---|
| `users` | `patients` |
| `user_id` | `patient_id` |
| `member_id`, `memberId` | `mem_id` |
| `schedule_id` | `sche_id` |
| `log`, `logs` | `activity`, `activities` |
| `log_id` | `activity_id` |
| `notification_id` | `noti_id` |
| `title` | `noti_title` |
| `message` | `noti_msg` |
| `type` | `noti_type` |
| `is_read` | `is_received` |
| `face_data` | `face_embeddings` |

주의:
- 단순 문자열 치환 금지.
- 이미 맞는 부분은 유지한다.
- 기존 프론트와 연결된 응답 key가 있으면 변경 전 영향 범위를 반드시 확인한다.
- `req.user` 기준 식별자는 `req.user.mem_id`를 유지한다.

---

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
| `admins` | 관리자 계정 |

지문 관련 현재 기준:
- `patients.fingerprint_slots`는 현재 다중 지문 슬롯 기준 컬럼이다.
- `patients.fingerprint_id`는 DDL에 남아 있는 레거시 단일 지문 ID 컬럼이다.
- 지문 슬롯 관리 로직을 수정할 때는 `fingerprint_id` 단일값 전제로 되돌리지 않는다.

---

## 관계도

```text
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

admins = 관리자 계정 독립 테이블
```

---

# 테이블 상세

## 1. medications

약 사전. 식약처 기준 공통 약품 정보.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `medi_id` | serial4 | PK | 자동 증가 ID |
| `item_seq` | varchar(50) | UNIQUE | 식약처 품목 일련번호 |
| `medi_name` | varchar(255) | ✓ | 약품명 |
| `medi_class` | varchar(100) | | 약품 분류 |

```sql
CREATE TABLE public.medications (
    medi_id serial4 PRIMARY KEY,
    item_seq varchar(50) UNIQUE,
    medi_name varchar(255) NOT NULL,
    medi_class varchar(100)
);

CREATE INDEX idx_medi_name_trgm
    ON public.medications USING gin (medi_name gin_trgm_ops);
```

주의:
- `medications.item_seq`는 UNIQUE다.
- `medications.medi_name`은 NOT NULL이다.
- 약 검색에는 `medi_name` 기준을 사용한다.
- `remaining_count` 같은 약 잔량 컬럼을 `medications`에 추가하지 않는다.
- 환자별 약 테이블이 아니라 공통 약 데이터이며, `schedules.medi_id`에서 참조한다.

---

## 2. members

보호자 계정. 소셜 로그인 계정 정보 관리 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `mem_id` | serial4 | PK | 자동 증가 ID |
| `social_id` | varchar(100) | ✓ | 소셜 제공자 고유 ID |
| `provider` | varchar(20) | ✓ | 소셜 제공자 (`kakao` / `naver` / `google`) |
| `email` | varchar(100) | ✓ | 이메일 |
| `nick` | varchar(50) | ✓ | 닉네임 |
| `profile_img` | text | ✓ | 프로필 이미지 URL |
| `joined_at` | timestamptz | ✓ | 가입일시 |

```sql
CREATE TABLE public.members (
    mem_id serial4 PRIMARY KEY,
    social_id varchar(100) NOT NULL,
    provider varchar(20) NOT NULL,
    email varchar(100) NOT NULL,
    nick varchar(50) NOT NULL,
    profile_img text NOT NULL,
    joined_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX ix_members_joined_at
    ON public.members (joined_at);

CREATE UNIQUE INDEX uq_members_email_nick
    ON public.members (email, nick);
```

주의:
- `members.mem_id`가 인증/회원 기준 PK다.
- JWT payload / `req.user` 기준 식별자는 `mem_id`다.
- `email + nick` 조합은 UNIQUE다.
- AI 작업자는 `mem_id`를 `member_id`, `memberId` 등으로 임의 변경하지 않는다.
- 현재 기준 DDL에는 `members.fcm_token` 컬럼을 사용하지 않는다. FCM 토큰은 `push_tokens` 테이블 기준이다.

---

## 3. patients

환자의 기본 인적 사항 및 건강 정보 저장 테이블. 보호자(`members`)에 종속된다.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `patient_id` | serial4 | PK | 자동 증가 ID |
| `mem_id` | int4 | ✓ | 보호자 FK → `members.mem_id` |
| `birthdate` | date | ✓ | 생년월일 |
| `gender` | bpchar(1) | ✓ | 성별 |
| `phone` | varchar(20) | ✓ | 전화번호 |
| `address` | varchar(255) | ✓ | 주소 |
| `bloodtype` | varchar(5) | ✓ | 혈액형 |
| `height` | numeric(5,2) | ✓ | 키 |
| `weight` | numeric(5,2) | ✓ | 몸무게 |
| `fingerprint_id` | int4 | ✓ | 레거시 단일 지문 ID 컬럼. 현재 신규 다중 지문 기준은 `fingerprint_slots` |
| `guardian_name` | varchar(100) | ✓ | 보호자/긴급 연락처 이름 |
| `guardian_phone` | varchar(20) | ✓ | 보호자/긴급 연락처 전화번호 |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `updated_at` | timestamptz | | 수정일시 |
| `deleted_at` | timestamptz | | 삭제일시 (소프트 삭제) |
| `patient_name` | varchar(100) | | 환자 이름 |
| `fingerprint_slots` | jsonb | ✓ | 다중 지문 슬롯 목록, 기본값 `[]` |

```sql
CREATE TABLE public.patients (
    patient_id serial4 PRIMARY KEY,
    mem_id int4 NOT NULL REFERENCES public.members(mem_id),
    birthdate date NOT NULL,
    gender bpchar(1) NOT NULL,
    phone varchar(20) NOT NULL,
    address varchar(255) NOT NULL,
    bloodtype varchar(5) NOT NULL,
    height numeric(5, 2) NOT NULL,
    weight numeric(5, 2) NOT NULL,
    fingerprint_id int4 NOT NULL,
    guardian_name varchar(100) NOT NULL,
    guardian_phone varchar(20) NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz,
    deleted_at timestamptz,
    patient_name varchar(100),
    fingerprint_slots jsonb DEFAULT '[]'::jsonb NOT NULL
);
```

`fingerprint_slots` 구조 예시:

```json
[
  { "slot_id": 1, "label": "지문1", "registered_at": "2026-04-30T10:00:00Z" },
  { "slot_id": 2, "label": "지문2", "registered_at": "2026-04-30T10:05:00Z" }
]
```

주의:
- `patients.mem_id`는 `members(mem_id)`를 참조한다.
- 예전 `users` 도메인은 최종적으로 `patients`다.
- 환자 식별자는 `patient_id`다.
- 환자명은 `patient_name` 컬럼을 사용한다.
- 현재 신규 다중 지문 슬롯 기준 컬럼은 `fingerprint_slots jsonb`다.
- `fingerprint_slots`는 기본값이 빈 배열이다.
- `fingerprint_id`는 현재 DDL에 남아 있는 레거시 단일 지문 ID 컬럼이므로, DB에서 제거되기 전까지 코드에서 존재하지 않는 컬럼처럼 취급하지 않는다.
- 신규 R307 다중 슬롯 등록/삭제 로직을 작성할 때는 `fingerprint_id` 단일값 전제 코드로 되돌리지 않는다.
- `deleted_at`이 존재하므로 환자 삭제/조회 로직에서 soft delete 여부를 확인해야 한다.
- AI 작업자는 `fingerprint_id`와 `fingerprint_slots`를 임의 삭제하거나 다른 방식으로 강제 통합하지 않는다.

---

## 4. schedules

환자의 복약 일정 등록 테이블. 환자별 약/시간 정의.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `sche_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `medi_id` | int4 | ✓ | 약품 FK → `medications.medi_id` |
| `start_date` | date | ✓ | 복약 시작일 |
| `end_date` | date | | 복약 종료일 |
| `time_to_take` | time | ✓ | 복약 시각 |
| `dose_interval` | int4 | | 복약 간격 |
| `status` | varchar(20) | ✓ | 스케줄 상태 |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `updated_at` | timestamptz | | 수정일시 |

```sql
CREATE TABLE public.schedules (
    sche_id serial4 PRIMARY KEY,
    patient_id int4 NOT NULL REFERENCES public.patients(patient_id),
    medi_id int4 NOT NULL REFERENCES public.medications(medi_id),
    start_date date NOT NULL,
    end_date date,
    time_to_take time NOT NULL,
    dose_interval int4,
    status varchar(20) NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz
);

CREATE INDEX ix_schedules_created_at
    ON public.schedules (created_at);
```

주의:
- 최종 기준은 `schedule_id`가 아니라 `sche_id`다.
- 하루 여러 번 복용은 `schedules` row를 여러 개 생성하는 방식이다.
- `time_to_take`는 time 타입이다.
- `start_date`는 NOT NULL, `end_date`는 NULL 가능하다.
- `remaining_count` 같은 잔량 컬럼은 `schedules`에 저장하지 않는다.
- AI 작업자는 하루 n회 복용 구조를 하나의 row + 배열 방식으로 임의 변경하지 않는다.
- KST 기준 날짜/시간 처리 규칙을 유지한다.

---

## 5. activities

디스펜서 인증 결과 및 실제 복약 기록 테이블. 스케줄 1회 실행 결과를 저장한다.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `activity_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `sche_id` | int4 | ✓ | 스케줄 FK → `schedules.sche_id` |
| `sche_time` | timestamptz | ✓ | 예정 복약 시각 |
| `actual_time` | timestamptz | | 실제 복약 시각 |
| `status` | varchar(20) | ✓ | 결과 상태 |
| `is_face_auth` | bool | ✓ | 얼굴 인증 성공 여부 |
| `is_ai_check` | bool | ✓ | AI 행동 인식 성공 여부 |
| `similarity_score` | numeric(5,4) | ✓ | 얼굴 유사도 점수 |
| `created_at` | timestamptz | ✓ | 생성일시 |

```sql
CREATE TABLE public.activities (
    activity_id serial4 PRIMARY KEY,
    patient_id int4 NOT NULL REFERENCES public.patients(patient_id),
    sche_id int4 NOT NULL REFERENCES public.schedules(sche_id),
    sche_time timestamptz NOT NULL,
    actual_time timestamptz,
    status varchar(20) NOT NULL,
    is_face_auth bool NOT NULL,
    is_ai_check bool NOT NULL,
    similarity_score numeric(5, 4) NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX ix_activities_created_at
    ON public.activities (created_at);

CREATE INDEX ix_activities_patient_sche_time
    ON public.activities (patient_id, sche_time);
```

주의:
- 예전 `logs` 도메인은 최종적으로 `activities`다.
- 예전 `log_id`는 `activity_id`다.
- 스케줄 FK는 `sche_id`다.
- 복약 상태는 `status` 컬럼을 기준으로 저장한다.
- `MISSED`는 배치 작업에서 생성하는 기존 정책을 유지한다.
- AI 작업자는 활동 로그 구조를 임의 변경하지 않는다.

---

## 6. devices

디스펜서 기기 정보 및 환자와의 연결 상태 관리 테이블. `device_uid`로 식별한다.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `device_id` | serial4 | PK | 자동 증가 ID |
| `device_uid` | varchar(100) | ✓ UNIQUE | 기기 고유 식별자 |
| `patient_id` | int4 | | 환자 FK → `patients.patient_id` |
| `device_status` | varchar(50) | | 기기 상태, 기본값 `UNREGISTERED` |
| `last_ping` | timestamptz | | 마지막 통신 시각 |
| `registered_at` | timestamptz | ✓ | 등록일시 |
| `device_name` | varchar(100) | ✓ | 기기 이름, 기본값 `UNKNOWN` |
| `alarm_sound_path` | text | | 알림음 파일 상대 경로 |
| `alarm_sound_name` | text | | 알림음 원본 파일명 |
| `alarm_sound_updated_at` | timestamptz | | 알림음 최종 업데이트 시각 |

```sql
CREATE TABLE public.devices (
    device_id serial4 PRIMARY KEY,
    device_uid varchar(100) NOT NULL UNIQUE,
    patient_id int4 REFERENCES public.patients(patient_id),
    device_status varchar(50) DEFAULT 'UNREGISTERED',
    last_ping timestamptz,
    registered_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    device_name varchar(100) DEFAULT 'UNKNOWN' NOT NULL,
    alarm_sound_path text,
    alarm_sound_name text,
    alarm_sound_updated_at timestamptz
);

CREATE INDEX ix_devices_registered_at
    ON public.devices (registered_at);
```

주의:
- `devices.device_uid`는 UNIQUE다.
- `devices.patient_id`는 `patients(patient_id)`를 참조한다.
- 기기 연결 상태는 `last_ping` 기준으로 계산한다.
- `device_name`, `alarm_sound_path`, `alarm_sound_name`, `alarm_sound_updated_at` 컬럼은 존재한다.
- AI 작업자는 `device_uid`, `device_status`, `last_ping` 흐름을 임의 변경하지 않는다.

---

## 7. face_embeddings

AI 모델에서 추출한 얼굴 특징 벡터 저장 테이블. pgvector 확장으로 얼굴 임베딩을 저장한다.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `face_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `face_vector` | public.vector | ✓ | 얼굴 임베딩 벡터 |
| `created_at` | timestamptz | ✓ | 생성일시 |

```sql
CREATE TABLE public.face_embeddings (
    face_id serial4 PRIMARY KEY,
    patient_id int4 NOT NULL REFERENCES public.patients(patient_id),
    face_vector public.vector NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX ix_face_embeddings_created_at
    ON public.face_embeddings (created_at);

CREATE INDEX ix_face_embeddings_face_vector
    ON public.face_embeddings (face_vector);

CREATE INDEX ix_face_embeddings_patient_id
    ON public.face_embeddings (patient_id);
```

주의:
- `face_embeddings.face_vector`는 `public.vector` 타입을 사용한다.
- AI 작업자는 `face_vector`를 text/json/float 배열로 임의 변경하지 않는다.
- 예전 `face_data` 류 이름이 남아 있으면 `face_embeddings` 기준으로 정리한다.
- 얼굴 임베딩 저장/조회 로직은 기존 타입 기준을 유지한다.

---

## 8. fingerprints

R307 센서 기준 지문 슬롯 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `fp_id` | serial4 | PK | 자동 증가 ID |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `slot_id` | int4 | ✓ | R307 센서 슬롯 번호 |
| `label` | varchar(50) | ✓ | 지문 표시명, 기본값 `지문` |
| `registered_at` | timestamptz | ✓ | 등록일시 |

```sql
CREATE TABLE public.fingerprints (
    fp_id serial4 PRIMARY KEY,
    patient_id int4 NOT NULL REFERENCES public.patients(patient_id),
    slot_id int4 NOT NULL,
    label varchar(50) NOT NULL DEFAULT '지문',
    registered_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (patient_id, slot_id)
);

CREATE INDEX ix_fingerprints_patient_id
    ON public.fingerprints (patient_id);
```

주의:
- `fingerprints.patient_id`는 `patients(patient_id)`를 참조한다.
- `patient_id + slot_id` 조합은 UNIQUE다.
- `patients.fingerprint_slots`는 환자 테이블의 신규 다중 지문 슬롯 컬럼이다.
- `patients.fingerprint_id`는 현재 DDL에 남아 있는 레거시 단일 지문 ID 컬럼이다.
- R307 슬롯 관리 기준은 실제 사용처에 따라 `fingerprints` 테이블 또는 `patients.fingerprint_slots` 중 하나를 확인해야 하며, 임의로 `fingerprint_id` 단일값 방식으로 되돌리지 않는다.
- AI 작업자는 지문 방식을 임의로 하나로 통합하거나 DB 스키마를 변경하지 않는다.
- `device.js` 병합 시 `/fingerprints` 라우트가 `fingerprints` 테이블 방식인지 `patients.fingerprint_slots` 방식인지 반드시 사용처를 확인한다.

---

## 9. voice_samples

보호자 목소리 파일. AI 처리 후 복약 알림 TTS에 사용한다.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `voice_id` | bigserial | PK | 자동 증가 ID |
| `patient_id` | int8 | ✓ | 환자 FK → `patients.patient_id`, ON DELETE CASCADE |
| `file_name` | varchar(255) | ✓ | 원본 파일명 |
| `file_path` | varchar(500) | ✓ | 서버 저장 경로 |
| `file_size` | int4 | ✓ | 파일 크기 |
| `mime_type` | varchar(100) | ✓ | MIME 타입 |
| `status` | varchar(20) | ✓ | 처리 상태 |
| `elevenlabs_voice_id` | varchar(255) | | ElevenLabs 연동 ID |
| `uploaded_at` | timestamptz | ✓ | 업로드 일시 |
| `updated_at` | timestamptz | ✓ | 수정일시 |

```sql
CREATE TABLE public.voice_samples (
    voice_id bigserial PRIMARY KEY,
    patient_id int8 NOT NULL REFERENCES public.patients(patient_id) ON DELETE CASCADE,
    file_name varchar(255) NOT NULL,
    file_path varchar(500) NOT NULL,
    file_size int4 NOT NULL,
    mime_type varchar(100) NOT NULL,
    status varchar(20) DEFAULT 'pending' NOT NULL,
    elevenlabs_voice_id varchar(255),
    uploaded_at timestamptz DEFAULT now() NOT NULL,
    updated_at timestamptz DEFAULT now() NOT NULL,
    CHECK (status IN ('pending', 'processing', 'ready', 'error'))
);
```

주의:
- `voice_samples.patient_id`는 `patients(patient_id)`를 참조한다.
- patient 삭제 시 `voice_samples`는 `ON DELETE CASCADE`로 함께 삭제된다.
- `status`는 pending / processing / ready / error 중 하나만 허용된다.
- 음성 파일 경로는 `file_path`에 저장한다.
- ElevenLabs 연동 ID는 `elevenlabs_voice_id`에 저장한다.
- AI 작업자는 `status` 값을 임의로 추가하거나 변경하지 않는다.
- `voice_samples.patient_id`는 int8이고 `patients.patient_id`는 int4이므로 코드에서 타입을 임의 변경하지 않는다.

---

## 10. notifications

FCM 푸시 알림 이력. 보호자에게 발송된 시스템 알림 내역 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `noti_id` | serial4 | PK | 자동 증가 ID |
| `mem_id` | int4 | ✓ | 보호자 FK → `members.mem_id` |
| `patient_id` | int4 | ✓ | 환자 FK → `patients.patient_id` |
| `activity_id` | int4 | ✓ | 복약 로그 FK → `activities.activity_id` |
| `noti_title` | varchar(255) | ✓ | 알림 제목 |
| `noti_msg` | text | ✓ | 알림 본문 |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `is_received` | bool | ✓ | FCM 수신/읽음 여부 |
| `received_time` | timestamptz | | FCM 수신 시각 |
| `noti_type` | varchar(50) | ✓ | 알림 유형 |

```sql
CREATE TABLE public.notifications (
    noti_id serial4 PRIMARY KEY,
    mem_id int4 NOT NULL REFERENCES public.members(mem_id),
    patient_id int4 NOT NULL REFERENCES public.patients(patient_id),
    activity_id int4 NOT NULL REFERENCES public.activities(activity_id),
    noti_title varchar(255) NOT NULL,
    noti_msg text NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_received bool NOT NULL,
    received_time timestamptz,
    noti_type varchar(50) NOT NULL
);

CREATE INDEX ix_notifications_created_at
    ON public.notifications (created_at);

CREATE INDEX ix_notifications_mem_received
    ON public.notifications (mem_id, is_received);
```

주의:
- `notifications.mem_id`는 `members(mem_id)`를 참조한다.
- `notifications.patient_id`는 `patients(patient_id)`를 참조한다.
- `notifications.activity_id`는 `activities(activity_id)`를 참조한다.
- 알림 읽음 여부는 `is_received` 기준이다.
- 알림 종류는 `noti_type` 컬럼을 사용한다.
- AI 작업자는 `noti_id`, `noti_title`, `noti_msg`, `noti_type` 응답 key를 임의 변경하지 않는다.
- activities 생성 시 알림 트리거 흐름은 기존 로직을 유지한다.

---

## 11. push_tokens

FCM 푸시 토큰. 보호자 기기별 토큰 관리.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `push_token_id` | serial4 | PK | 자동 증가 ID |
| `mem_id` | int4 | ✓ | 보호자 FK → `members.mem_id` |
| `fcm_token` | text | ✓ UNIQUE | FCM 등록 토큰 |
| `device_type` | varchar(20) | ✓ | 기기 유형, 기본값 `web` |
| `is_active` | bool | ✓ | 활성 여부 |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `updated_at` | timestamptz | ✓ | 수정일시, 트리거로 자동 갱신 |

```sql
CREATE TABLE public.push_tokens (
    push_token_id serial4 PRIMARY KEY,
    mem_id int4 NOT NULL REFERENCES public.members(mem_id),
    fcm_token text NOT NULL UNIQUE,
    device_type varchar(20) DEFAULT 'web' NOT NULL,
    is_active bool DEFAULT true NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX ix_push_tokens_mem_id_is_active
    ON public.push_tokens (mem_id, is_active);

CREATE TRIGGER trg_push_tokens_updated_at
BEFORE UPDATE ON public.push_tokens
FOR EACH ROW
EXECUTE FUNCTION set_push_tokens_updated_at();
```

주의:
- `push_tokens.mem_id`는 `members(mem_id)`를 참조한다.
- `fcm_token`은 UNIQUE다.
- 같은 FCM 토큰은 중복 저장하지 않고 갱신해야 한다.
- `device_type` 기본값은 `web`이다.
- `is_active` 기준으로 활성 토큰을 구분한다.
- `updated_at`은 `set_push_tokens_updated_at()` 트리거로 갱신된다.
- 로그인 시 FCM 토큰 갱신 흐름과 activities 생성 시 알림 트리거 흐름을 유지한다.

---

## 12. admins

관리자 계정 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `admin_id` | serial4 | PK | 자동 증가 ID |
| `login_id` | varchar(50) | ✓ UNIQUE | 관리자 로그인 ID |
| `password` | varchar(255) | ✓ | 비밀번호 해시 또는 저장값 |
| `name` | varchar(50) | ✓ | 관리자 이름 |
| `role` | varchar(20) | ✓ | 권한, 기본값 `admin` |
| `is_active` | bool | ✓ | 활성 여부 |
| `created_at` | timestamptz | ✓ | 생성일시 |
| `last_login_at` | timestamptz | | 마지막 로그인 시각 |

```sql
CREATE TABLE public.admins (
    admin_id serial4 PRIMARY KEY,
    login_id varchar(50) NOT NULL UNIQUE,
    password varchar(255) NOT NULL,
    name varchar(50) NOT NULL,
    role varchar(20) DEFAULT 'admin' NOT NULL,
    is_active bool DEFAULT true NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at timestamptz
);
```

## 지문 컬럼 최종 기준

현재 DB 기준에서 `patients.fingerprint_id` 컬럼은 삭제되었다.

따라서 AI 작업자는 아래 규칙을 반드시 따른다.

- `patients.fingerprint_id`를 조회/INSERT/UPDATE/RETURNING 하지 않는다.
- `fingerprint_id` 요청 key 또는 응답 key를 신규 코드에 추가하지 않는다.
- `POST /api/device/fingerprint`처럼 `fingerprint_id` 단일값을 저장하는 레거시 라우트는 제거 또는 미사용 처리 대상이다.
- 신규 다중 지문 슬롯 기준은 `patients.fingerprint_slots`다.
- `/api/device/fingerprints` 라우트는 `fingerprint_slots jsonb` 기준으로 조회/등록/삭제한다.
- `fingerprint_slots` 구조는 `{ slot_id, label, registered_at }` 배열을 유지한다.
- `fingerprints` 테이블이 남아 있더라도, 현재 공식 기준이 `patients.fingerprint_slots`라면 임의로 `fingerprints` 테이블 방식으로 되돌리지 않는다.
- DB 스키마를 다시 변경하거나 `fingerprint_id` 컬럼을 재추가하지 않는다.

주의:
- 관리자 API는 `/api/admin/*` 기준으로 관리한다.
- `adminAuth` 적용 흐름을 임의 변경하지 않는다.
- `login_id`, `password`, `role`, `is_active` 컬럼명을 임의 변경하지 않는다.

---

# 코드 반영 규칙

## req.user

- `req.user.mem_id` 기준 사용
- `req.user.member_id`, `req.user.memberId` 사용 금지
- 인증(JWT/req.user/verifyToken) 로직 임의 수정 금지

## SQL

- `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `JOIN` 모두 최종 컬럼명 기준 사용
- SQL alias에 예전 이름을 남기지 말 것
- 금지 예시:
  - `AS user_id`
  - `AS schedule_id`
  - `AS log_id`
  - `AS notification_id`

## API 요청/응답

- 외부 인터페이스는 `snake_case` 기준
- 요청 body / params / response json 모두 최종 컬럼명 기준으로 맞춤
- 프론트와 연결된 응답 key는 임의 변경하지 말고 영향 범위를 먼저 확인
- 응답은 기존 `sendSuccess` / `sendError` 구조 유지

## AI 작업 금지 사항

- 전체 재작성 금지
- DB 스키마 수정 금지
- 새 마이그레이션 파일 생성 금지
- 새 테이블/새 컬럼 임의 추가 금지
- 기존 로직 삭제 금지
- UI/UX 변경 금지
- 라우트명 변경 금지
- 응답 key 변경 금지
- 인증 로직 수정 금지
- 외부 라이브러리 추가 금지
- 파일/폴더 구조 변경 금지

## 최종 체크 포인트

아래 항목이 코드에 남아 있으면 반드시 문맥 기준으로 검토한다.

- `users`
- `user_id`
- `member_id`
- `memberId`
- `schedule_id`
- `log`
- `logs`
- `log_id`
- `notification_id`
- `title`
- `message`
- `type`
- `is_read`
- `face_data`

주의:
- `log`, `title`, `message`, `type`은 일반 단어로도 쓰일 수 있으므로 무조건 치환하지 않는다.
- 코드 맥락이 DB/API 네이밍과 관련될 때만 수정 여부를 판단한다.
