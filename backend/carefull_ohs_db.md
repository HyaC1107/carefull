# Carefull — Database Schema & AI 작업 기준 (fingerprint_slots 반영본)

이 문서는 업로드된 최신 `ddl.txt`를 기준으로 정리한 Carefull 프로젝트 DB 기준 문서다.

## 문서 사용 원칙

아래 내용은 현재 프로젝트의 DB 구조를 설명하기 위한 **문서용 기준**이다.
AI/Codex 작업자는 이 문서를 근거로 코드의 SQL, API 요청/응답 key, 라우트 변수명을 검수한다.

금지:
- DB 스키마 임의 수정
- 새 마이그레이션 파일 생성
- 새 테이블/새 컬럼 임의 추가
- 존재하지 않는 컬럼 추측 사용
- `fingerprint_id` 단일 지문 방식 복구
- `fingerprints` 테이블 방식 복구
- 전체 코드/전체 파일 재작성

유지:
- `req.user.mem_id`
- `patient_id`, `device_uid`, `sche_id`, `medi_id`, `activity_id`, `noti_id`
- API 요청/응답 key는 `snake_case`
- 응답 구조는 기존 `sendSuccess` / `sendError`

---

## 최종 테이블 목록

| 테이블 | 설명 |
|---|---|
| `admins` | 관리자 계정 |
| `medications` | 약 사전 |
| `members` | 보호자/회원 소셜 로그인 계정 |
| `patients` | 환자 정보 및 다중 지문 슬롯 |
| `push_tokens` | FCM 푸시 토큰 |
| `schedules` | 복약 스케줄 |
| `voice_samples` | 보호자 음성 샘플 |
| `activities` | 복약 활동/로그 |
| `devices` | 디스펜서 기기 |
| `face_embeddings` | 얼굴 임베딩 벡터 |
| `notifications` | 알림 이력 |

## 삭제/미사용 확정

| 항목 | 최종 기준 |
|---|---|
| `patients.fingerprint_id` | 현재 DDL에 없음. 조회/INSERT/UPDATE/RETURNING 금지 |
| `fingerprints` 테이블 | 현재 DDL에 없음. SELECT/INSERT/UPDATE/DELETE 금지 |
| `fp_id` | 사용 금지 |
| `fingerprint_id` 요청/응답 key | 신규 코드 추가 금지 |

지문 공식 저장 기준은 오직 `patients.fingerprint_slots`다.

---

# 1. admins

관리자 계정 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `admin_id` | serial4 | PK | 관리자 ID |
| `login_id` | varchar(50) | UNIQUE, NOT NULL | 로그인 ID |
| `password` | varchar(255) | NOT NULL | 비밀번호 |
| `name` | varchar(50) | NOT NULL | 관리자 이름 |
| `role` | varchar(20) | NOT NULL, default `admin` | 권한 |
| `is_active` | bool | NOT NULL, default true | 활성 여부 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |
| `last_login_at` | timestamptz | NULL | 마지막 로그인 |

```sql
CREATE TABLE public.admins (
    admin_id serial4 NOT NULL,
    login_id varchar(50) NOT NULL,
    "password" varchar(255) NOT NULL,
    "name" varchar(50) NOT NULL,
    "role" varchar(20) DEFAULT 'admin'::character varying NOT NULL,
    is_active bool DEFAULT true NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login_at timestamptz NULL,
    CONSTRAINT admins_pkey PRIMARY KEY (admin_id),
    CONSTRAINT uq_admins_login_id UNIQUE (login_id)
);
```

---

# 2. medications

약 사전 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `medi_id` | serial4 | PK | 약 ID |
| `item_seq` | varchar(50) | UNIQUE, NULL | 식약처 품목 일련번호 |
| `medi_name` | varchar(255) | NOT NULL | 약품명 |
| `medi_class` | varchar(100) | NULL | 약품 분류 |

```sql
CREATE TABLE public.medications (
    medi_id serial4 NOT NULL,
    item_seq varchar(50) NULL,
    medi_name varchar(255) NOT NULL,
    medi_class varchar(100) NULL,
    CONSTRAINT medications_pkey PRIMARY KEY (medi_id),
    CONSTRAINT uq_item_seq UNIQUE (item_seq)
);
CREATE INDEX idx_medi_name_trgm ON public.medications USING gin (medi_name gin_trgm_ops);
```

주의:
- 환자별 약 테이블이 아니라 공통 약 사전이다.
- `schedules.medi_id`에서 참조한다.

---

# 3. members

보호자/회원 소셜 로그인 계정 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `mem_id` | serial4 | PK | 회원 ID |
| `social_id` | varchar(100) | NOT NULL | 소셜 제공자 ID |
| `provider` | varchar(20) | NOT NULL | kakao/google/naver |
| `email` | varchar(100) | NOT NULL | 이메일 |
| `nick` | varchar(50) | NOT NULL | 닉네임 |
| `profile_img` | text | NOT NULL | 프로필 이미지 |
| `joined_at` | timestamptz | NOT NULL | 가입 시각 |

```sql
CREATE TABLE public.members (
    mem_id serial4 NOT NULL,
    social_id varchar(100) NOT NULL,
    provider varchar(20) NOT NULL,
    email varchar(100) NOT NULL,
    nick varchar(50) NOT NULL,
    profile_img text NOT NULL,
    joined_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT members_pkey PRIMARY KEY (mem_id)
);
CREATE INDEX ix_members_1 ON public.members USING btree (joined_at);
CREATE UNIQUE INDEX uq_members_1 ON public.members USING btree (email, nick);
CREATE UNIQUE INDEX uq_members_social ON public.members USING btree (social_id, provider);
```

주의:
- JWT payload / `req.user` 기준 식별자는 `mem_id`다.
- FCM 토큰은 `members`가 아니라 `push_tokens` 테이블 기준이다.

---

# 4. patients

환자 기본 정보 및 다중 지문 슬롯 저장 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `patient_id` | serial4 | PK | 환자 ID |
| `mem_id` | int4 | FK, NOT NULL | 보호자 회원 FK |
| `birthdate` | date | NOT NULL | 생년월일 |
| `gender` | bpchar(1) | NOT NULL | 성별 |
| `phone` | varchar(20) | NOT NULL | 연락처 |
| `address` | varchar(255) | NOT NULL | 주소 |
| `bloodtype` | varchar(5) | NOT NULL | 혈액형 |
| `height` | numeric(5,2) | NOT NULL | 키 |
| `weight` | numeric(5,2) | NOT NULL | 몸무게 |
| `guardian_name` | varchar(100) | NOT NULL | 보호자 이름 |
| `guardian_phone` | varchar(20) | NOT NULL | 보호자 연락처 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |
| `updated_at` | timestamptz | NULL | 수정 시각 |
| `deleted_at` | timestamptz | NULL | 소프트 삭제 시각 |
| `patient_name` | varchar(100) | NULL | 환자 이름 |
| `fingerprint_slots` | jsonb | NOT NULL, default `[]` | R307 다중 지문 슬롯 배열 |

```sql
CREATE TABLE public.patients (
    patient_id serial4 NOT NULL,
    mem_id int4 NOT NULL,
    birthdate date NOT NULL,
    gender bpchar(1) NOT NULL,
    phone varchar(20) NOT NULL,
    address varchar(255) NOT NULL,
    bloodtype varchar(5) NOT NULL,
    height numeric(5, 2) NOT NULL,
    weight numeric(5, 2) NOT NULL,
    guardian_name varchar(100) NOT NULL,
    guardian_phone varchar(20) NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz NULL,
    deleted_at timestamptz NULL,
    patient_name varchar(100) NULL,
    fingerprint_slots jsonb DEFAULT '[]'::jsonb NOT NULL,
    CONSTRAINT patients_pkey PRIMARY KEY (patient_id),
    CONSTRAINT fk_patients_mem_id_members_mem_id FOREIGN KEY (mem_id) REFERENCES public.members(mem_id)
);
```

`fingerprint_slots` 구조:

```json
[
  {
    "slot_id": 1,
    "label": "지문",
    "registered_at": "2026-04-30T02:06:40.199Z"
  },
  {
    "slot_id": 2,
    "label": "지문",
    "registered_at": "2026-04-30T02:06:54.535Z"
  }
]
```

지문 저장 최종 기준:
- `fingerprint_slots`는 `jsonb DEFAULT '[]'::jsonb NOT NULL`이다.
- `fingerprint_slots`는 int4가 아니다.
- `patients.fingerprint_id`는 현재 DDL에 없다.
- `patients.fingerprint_id`를 SELECT / INSERT / UPDATE / RETURNING 하지 않는다.
- `fingerprints` 테이블에 지문을 저장하지 않는다.
- `/api/device/fingerprints`는 `patients.fingerprint_slots` 기준으로 동작해야 한다.
- `POST /api/device/fingerprint` 같은 단일 지문 legacy 흐름은 신규 저장 기준으로 사용하지 않는다. 유지해야 한다면 내부에서 `fingerprint_slots`로만 매핑한다.
- `fp_id` 요청/응답 key를 신규로 만들지 않는다.

---

# 5. push_tokens

FCM 푸시 토큰 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `push_token_id` | serial4 | PK | 토큰 ID |
| `mem_id` | int4 | FK, NOT NULL | 회원 FK |
| `fcm_token` | text | UNIQUE, NOT NULL | FCM 토큰 |
| `device_type` | varchar(20) | NOT NULL, default `web` | 기기 유형 |
| `is_active` | bool | NOT NULL, default true | 활성 여부 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |
| `updated_at` | timestamptz | NOT NULL | 수정 시각 |

```sql
CREATE TABLE public.push_tokens (
    push_token_id serial4 NOT NULL,
    mem_id int4 NOT NULL,
    fcm_token text NOT NULL,
    device_type varchar(20) DEFAULT 'web'::character varying NOT NULL,
    is_active bool DEFAULT true NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT push_tokens_pkey PRIMARY KEY (push_token_id),
    CONSTRAINT uq_push_tokens_fcm_token UNIQUE (fcm_token),
    CONSTRAINT fk_push_tokens_mem_id_members_mem_id FOREIGN KEY (mem_id) REFERENCES public.members(mem_id)
);
CREATE INDEX ix_push_tokens_mem_id_is_active ON public.push_tokens USING btree (mem_id, is_active);
```

주의:
- 같은 FCM 토큰은 중복 저장하지 않는다.
- 활성 토큰 조회는 `mem_id`, `is_active` 기준이다.

---

# 6. schedules

복약 스케줄 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `sche_id` | serial4 | PK | 스케줄 ID |
| `patient_id` | int4 | FK, NOT NULL | 환자 FK |
| `medi_id` | int4 | FK, NOT NULL | 약 FK |
| `start_date` | date | NOT NULL | 시작일 |
| `end_date` | date | NULL | 종료일 |
| `time_to_take` | time | NOT NULL | 복약 시각 |
| `dose_interval` | int4 | NOT NULL, default 1 | 복약 간격 |
| `status` | varchar(20) | NOT NULL | 상태 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |
| `updated_at` | timestamptz | NULL | 수정 시각 |

```sql
CREATE TABLE public.schedules (
    sche_id serial4 NOT NULL,
    patient_id int4 NOT NULL,
    medi_id int4 NOT NULL,
    start_date date NOT NULL,
    end_date date NULL,
    time_to_take time NOT NULL,
    dose_interval int4 DEFAULT 1 NOT NULL,
    status varchar(20) NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamptz NULL,
    CONSTRAINT schedules_pkey PRIMARY KEY (sche_id),
    CONSTRAINT fk_schedules_medi_id_medications_medi_id FOREIGN KEY (medi_id) REFERENCES public.medications(medi_id),
    CONSTRAINT fk_schedules_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_schedules_1 ON public.schedules USING btree (created_at);
```

주의:
- `dose_interval`은 `DEFAULT 1 NOT NULL`이다.
- 코드에서 `dose_interval = null`을 명시 INSERT하지 않는다.
- 하루 여러 번 복약은 row 여러 개로 저장한다.
- `sche_id`를 `schedule_id`로 되돌리지 않는다.

---

# 7. voice_samples

보호자 음성 샘플 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `voice_id` | bigserial | PK | 음성 ID |
| `patient_id` | int4 | FK, NOT NULL | 환자 FK |
| `file_name` | varchar(255) | NOT NULL | 파일명 |
| `file_path` | varchar(500) | NOT NULL | 파일 경로 |
| `file_size` | int4 | NOT NULL | 파일 크기 |
| `mime_type` | varchar(100) | NOT NULL | MIME 타입 |
| `status` | varchar(20) | NOT NULL, default `pending` | 처리 상태 |
| `elevenlabs_voice_id` | varchar(255) | NULL | ElevenLabs voice ID |
| `uploaded_at` | timestamptz | NOT NULL | 업로드 시각 |
| `updated_at` | timestamptz | NOT NULL | 수정 시각 |

```sql
CREATE TABLE public.voice_samples (
    voice_id bigserial NOT NULL,
    patient_id int4 NOT NULL,
    file_name varchar(255) NOT NULL,
    file_path varchar(500) NOT NULL,
    file_size int4 NOT NULL,
    mime_type varchar(100) NOT NULL,
    status varchar(20) DEFAULT 'pending'::character varying NOT NULL,
    elevenlabs_voice_id varchar(255) NULL,
    uploaded_at timestamptz DEFAULT now() NOT NULL,
    updated_at timestamptz DEFAULT now() NOT NULL,
    CONSTRAINT uq_voice_samples_patient_id UNIQUE (patient_id),
    CONSTRAINT voice_samples_pkey PRIMARY KEY (voice_id),
    CONSTRAINT voice_samples_status_check CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'ready'::character varying, 'error'::character varying])::text[]))),
    CONSTRAINT voice_samples_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id) ON DELETE CASCADE
);
```

---

# 8. activities

복약 활동/로그 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `activity_id` | serial4 | PK | 활동 ID |
| `patient_id` | int4 | FK, NOT NULL | 환자 FK |
| `sche_id` | int4 | FK, NOT NULL | 스케줄 FK |
| `sche_time` | timestamptz | NOT NULL | 예정 복약 시각 |
| `actual_time` | timestamptz | NULL | 실제 복약 시각 |
| `status` | varchar(20) | NOT NULL | 상태 |
| `is_face_auth` | bool | NOT NULL | 얼굴 인증 여부 |
| `is_ai_check` | bool | NOT NULL | AI 확인 여부 |
| `similarity_score` | numeric(5,4) | NULL | 유사도 점수 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |

```sql
CREATE TABLE public.activities (
    activity_id serial4 NOT NULL,
    patient_id int4 NOT NULL,
    sche_id int4 NOT NULL,
    sche_time timestamptz NOT NULL,
    actual_time timestamptz NULL,
    status varchar(20) NOT NULL,
    is_face_auth bool NOT NULL,
    is_ai_check bool NOT NULL,
    similarity_score numeric(5, 4) NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT activities_pkey PRIMARY KEY (activity_id),
    CONSTRAINT fk_activities_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id),
    CONSTRAINT fk_activities_sche_id_schedules_sche_id FOREIGN KEY (sche_id) REFERENCES public.schedules(sche_id)
);
CREATE INDEX ix_activities_1 ON public.activities USING btree (created_at);
CREATE INDEX ix_activities_2 ON public.activities USING btree (patient_id, sche_time);
```

주의:
- `logs`가 아니라 `activities`다.
- `log_id`가 아니라 `activity_id`다.
- 스케줄 FK는 `sche_id`다.

---

# 9. devices

디스펜서 기기 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `device_id` | serial4 | PK | 기기 ID |
| `device_uid` | varchar(100) | UNIQUE, NOT NULL | 기기 고유값 |
| `patient_id` | int4 | FK, NULL | 환자 FK |
| `device_status` | varchar(50) | NULL, default `UNREGISTERED` | 기기 상태 |
| `last_ping` | timestamptz | NULL | 마지막 통신 |
| `registered_at` | timestamptz | NOT NULL | 등록 시각 |
| `device_name` | varchar(100) | NOT NULL, default `UNKNOWN` | 기기명 |
| `alarm_sound_path` | text | NULL | 알림음 경로 |
| `alarm_sound_name` | text | NULL | 알림음 파일명 |
| `alarm_sound_updated_at` | timestamptz | NULL | 알림음 수정 시각 |

```sql
CREATE TABLE public.devices (
    device_id serial4 NOT NULL,
    device_uid varchar(100) NOT NULL,
    patient_id int4 NULL,
    device_status varchar(50) DEFAULT 'UNREGISTERED'::character varying NULL,
    last_ping timestamptz NULL,
    registered_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    device_name varchar(100) DEFAULT 'UNKNOWN'::character varying NOT NULL,
    alarm_sound_path text NULL,
    alarm_sound_name text NULL,
    alarm_sound_updated_at timestamptz NULL,
    CONSTRAINT devices_device_uid_key UNIQUE (device_uid),
    CONSTRAINT devices_pkey PRIMARY KEY (device_id),
    CONSTRAINT fk_devices_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_devices_1 ON public.devices USING btree (registered_at);
```

주의:
- 지문 데이터는 `devices`나 `fingerprints`가 아니라 `patients.fingerprint_slots`에 저장한다.

---

# 10. face_embeddings

얼굴 임베딩 벡터 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `face_id` | serial4 | PK | 얼굴 벡터 ID |
| `patient_id` | int4 | FK, NOT NULL | 환자 FK |
| `face_vector` | public.vector | NOT NULL | 얼굴 벡터 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |

```sql
CREATE TABLE public.face_embeddings (
    face_id serial4 NOT NULL,
    patient_id int4 NOT NULL,
    face_vector public.vector NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT face_embeddings_pkey PRIMARY KEY (face_id),
    CONSTRAINT fk_face_embeddings_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_face_embeddings_1 ON public.face_embeddings USING btree (created_at);
CREATE INDEX ix_face_embeddings_2 ON public.face_embeddings USING hnsw (face_vector vector_cosine_ops);
CREATE INDEX ix_face_embeddings_3 ON public.face_embeddings USING btree (patient_id);
```

---

# 11. notifications

보호자 알림 이력 테이블.

| 컬럼 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `noti_id` | serial4 | PK | 알림 ID |
| `mem_id` | int4 | FK, NOT NULL | 회원 FK |
| `patient_id` | int4 | FK, NOT NULL | 환자 FK |
| `activity_id` | int4 | FK, NULL | 활동 FK |
| `noti_title` | varchar(255) | NOT NULL | 알림 제목 |
| `noti_msg` | text | NOT NULL | 알림 본문 |
| `created_at` | timestamptz | NOT NULL | 생성 시각 |
| `is_received` | bool | NOT NULL | 수신/읽음 여부 |
| `received_time` | timestamptz | NULL | 수신 시각 |
| `noti_type` | varchar(50) | NOT NULL | 알림 유형 |

```sql
CREATE TABLE public.notifications (
    noti_id serial4 NOT NULL,
    mem_id int4 NOT NULL,
    patient_id int4 NOT NULL,
    activity_id int4 NULL,
    noti_title varchar(255) NOT NULL,
    noti_msg text NOT NULL,
    created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
    is_received bool NOT NULL,
    received_time timestamptz NULL,
    noti_type varchar(50) NOT NULL,
    CONSTRAINT notifications_pkey PRIMARY KEY (noti_id),
    CONSTRAINT fk_notifications_activity_id_activities_activity_id FOREIGN KEY (activity_id) REFERENCES public.activities(activity_id),
    CONSTRAINT fk_notifications_mem_id_members_mem_id FOREIGN KEY (mem_id) REFERENCES public.members(mem_id),
    CONSTRAINT fk_notifications_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_notifications_1 ON public.notifications USING btree (created_at);
CREATE INDEX ix_notifications_2 ON public.notifications USING btree (mem_id, is_received);
```

주의:
- `title`, `message`, `type`, `is_read`로 되돌리지 않는다.
- `activity_id`는 현재 DDL 기준 NULL 가능하다.

---

# 관계 요약

```text
members.mem_id ──< patients.mem_id
members.mem_id ──< push_tokens.mem_id
patients.patient_id ──< devices.patient_id
patients.patient_id ──< schedules.patient_id
patients.patient_id ──< activities.patient_id
patients.patient_id ──< face_embeddings.patient_id
patients.patient_id ──< voice_samples.patient_id
patients.patient_id ──< notifications.patient_id
medications.medi_id ──< schedules.medi_id
schedules.sche_id ──< activities.sche_id
activities.activity_id ──< notifications.activity_id
```

---

# 코드 반영 규칙

## req.user

- `req.user.mem_id` 기준 사용
- `req.user.member_id`, `req.user.memberId` 사용 금지
- 인증/JWT/verifyToken 흐름 임의 수정 금지

## SQL

- 현재 DDL에 있는 테이블/컬럼만 사용
- `patients.fingerprint_id` 사용 금지
- `fingerprints` 테이블 사용 금지
- SQL alias에 구명칭을 남기지 않는다

금지 예시:

```sql
SELECT fingerprint_id FROM patients;
INSERT INTO fingerprints (...);
UPDATE fingerprints SET ...;
SELECT fp_id FROM fingerprints;
```

## API 요청/응답

- 외부 인터페이스는 `snake_case`
- 기존 프론트와 연결된 응답 key는 임의 변경 금지
- 지문 관련 신규 기준은 `fingerprint_slots`
- `fingerprint_slots`는 배열 형태 JSONB로 취급

## 지문 관련 최종 금지 사항

아래 문자열/구조가 코드에 남아 있으면 반드시 검토한다.

```text
patients.fingerprint_id
p.fingerprint_id
fingerprint_id SELECT/INSERT/UPDATE/RETURNING
CREATE TABLE public.fingerprints
FROM fingerprints
JOIN fingerprints
INSERT INTO fingerprints
UPDATE fingerprints
DELETE FROM fingerprints
fp_id
```

주의:
- 문서 설명상 단어로 `fingerprints`가 나올 수는 있으나, 코드/SQL 기준으로 테이블 사용은 금지다.
- `fingerprint_slots`는 반드시 `jsonb`다.
- `fingerprint_slots`를 `int4`로 작성하지 않는다.

---

# AI/Codex 작업 지침

작업 전 반드시 이 문서를 읽는다.

수정 시:
1. 현재 코드와 이 명세를 비교한다.
2. 이미 맞는 부분은 유지한다.
3. 불일치하는 부분만 최소 수정한다.
4. DB 스키마는 수정하지 않는다.
5. `fingerprints` 테이블 방식으로 되돌리지 않는다.
6. `fingerprint_slots`를 `jsonb` 배열로 유지한다.
7. 전체 코드 출력 금지, 수정 파일 목록과 핵심 diff만 출력한다.

검수 명령 예시:

```bash
rg -n "patients\.fingerprint_id|p\.fingerprint_id|SELECT.*fingerprint_id|INSERT.*fingerprint_id|UPDATE.*fingerprint_id|RETURNING.*fingerprint_id|FROM\s+fingerprints|JOIN\s+fingerprints|INSERT\s+INTO\s+fingerprints|UPDATE\s+fingerprints|DELETE\s+FROM\s+fingerprints|fp_id" backend frontend raspberry
```

위 검색 결과가 코드/SQL 실행 경로에 남아 있으면 현재 DB 기준과 불일치한다.
