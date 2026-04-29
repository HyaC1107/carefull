# Carefull Final Table Spec

이 파일은 케어풀 프로젝트의 **최종 테이블 명세 기준**이다.  
서버 코드, SQL, API 응답/요청 키, 라우트 변수명 정리는 이 파일 기준으로 맞춘다.

## 기준 원칙

- 최종 기준 테이블:
  - `members`
  - `patients`
  - `devices`
  - `medications`
  - `schedules`
  - `face_embeddings`
  - `activities`
  - `notifications`

- 네이밍 규칙:
  - DB 컬럼명 / API 요청 키 / API 응답 키 / SQL alias = `snake_case`
  - 예전 명칭이 남아 있으면 최종 명칭으로 수정
  - 단순 문자열 치환이 아니라 문맥 기준으로 수정

## 반드시 반영할 이름 변경 규칙

- `users` → `patients`
- `user_id` → `patient_id`
- `member_id` → `mem_id`
- `schedule_id` → `sche_id`
- `log`, `logs` → `activity`, `activities`
- `log_id` → `activity_id`
- `notification_id` → `noti_id`
- `title` → `noti_title`
- `message` → `noti_msg`
- `type` → `noti_type`
- `is_read` → `is_received`

## 1. members

소셜 로그인 계정(보호자 회원) 정보 관리 테이블

### columns
- `mem_id`
- `social_id`
- `provider`
- `email`
- `nick`
- `profile_img`
- `joined_at`

### notes
- `mem_id`는 회원 식별자
- `provider`는 `kakao`, `google`, `naver`
- JWT payload / `req.user` 기준 식별자는 `mem_id`

---

## 2. patients

환자의 기본 인적 사항 및 건강 정보 저장 테이블

### columns
- `patient_id`
- `mem_id`
- `birthdate`
- `gender`
- `phone`
- `address`
- `bloodtype`
- `height`
- `weight`
- `fingerprint_id`
- `guardian_name`
- `guardian_phone`
- `created_at`
- `updated_at`
- `deleted_at`

### notes
- 예전 `users` 도메인은 최종적으로 `patients`
- 환자 식별자는 `patient_id`
- 회원과 환자는 `mem_id`로 연결

---

## 3. devices

디스펜서 기기 정보 및 환자와의 연결 상태 관리 테이블

### columns
- `device_id`
- `device_uid`
- `patient_id`
- `device_status`
- `last_ping`
- `registered_at`

### notes
- 기기 상태값은 프로젝트 코드 기준 ENUM/상수로 관리 가능
- 환자 연결 키는 `patient_id`

---

## 4. medications

식약처 기반 공통 약 사전 테이블

### columns
- `medi_id`
- `item_seq`
- `medi_name`

### notes
- 환자별 약 테이블이 아니라 공통 약 데이터
- 스케줄 테이블에서 `medi_id`를 참조

---

## 5. schedules

환자의 복약 일정 등록 테이블

### columns
- `sche_id`
- `patient_id`
- `medi_id`
- `start_date`
- `end_date`
- `time_to_take`
- `dose_interval`
- `status`
- `created_at`
- `updated_at`

### notes
- 최종 기준은 `schedule_id`가 아니라 `sche_id`
- 예전 `schedule_id` 명칭이 남아 있으면 전부 검토 대상
- 프론트 요청 body / params / 응답 키도 `sche_id` 기준 확인 필요

---

## 6. face_embeddings

AI 모델에서 추출한 얼굴 특징 벡터 저장 테이블

### columns
- `face_id`
- `patient_id`
- `face_vector`
- `created_at`

### notes
- 예전 `face_data` 류 이름이 남아 있으면 `face_embeddings` 기준으로 정리
- 환자 식별 키는 `patient_id`

---

## 7. activities

디스펜서 인증 결과 및 실제 복약 기록 테이블

### columns
- `activity_id`
- `patient_id`
- `sche_id`
- `sche_time`
- `actual_time`
- `status`
- `is_face_auth`
- `is_ai_check`
- `similarity_score`
- `created_at`

### notes
- 예전 `logs` 도메인은 최종적으로 `activities`
- 예전 `log_id`는 `activity_id`
- 스케줄 FK는 `sche_id`
- 얼굴 인증, AI 판별, 유사도 점수까지 포함
- 기존 코드에서 이미 `activity`로 바뀐 부분은 유지하고, 남은 구명칭만 수정

---

## 8. notifications

보호자에게 발송된 시스템 알림 내역 테이블

### columns
- `noti_id`
- `mem_id`
- `patient_id`
- `activity_id`
- `noti_title`
- `noti_msg`
- `created_at`
- `is_received`
- `received_time`
- `noti_type`

### notes
- 예전 알림 필드명(`notification_id`, `title`, `message`, `type`, `is_read`)은 최종 필드명으로 정리
- 회원 식별자는 `mem_id`
- 환자 식별자는 `patient_id`
- 활동 식별자는 `activity_id`

---

# 관계 요약

- `members.mem_id` → `patients.mem_id`
- `patients.patient_id` → `devices.patient_id`
- `patients.patient_id` → `schedules.patient_id`
- `medications.medi_id` → `schedules.medi_id`
- `patients.patient_id` → `face_embeddings.patient_id`
- `patients.patient_id` → `activities.patient_id`
- `schedules.sche_id` → `activities.sche_id`
- `members.mem_id` → `notifications.mem_id`
- `patients.patient_id` → `notifications.patient_id`
- `activities.activity_id` → `notifications.activity_id`

# 코드 반영 규칙

## req.user
- `req.user.mem_id` 기준 사용
- `req.user.member_id`, `req.user.memberId` 사용 금지

## SQL
- `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `JOIN` 모두 최종 컬럼명 기준 사용
- SQL alias에 예전 이름을 남기지 말 것
- 예:
  - 금지: `AS user_id`
  - 금지: `AS schedule_id`
  - 금지: `AS log_id`

## API 요청/응답
- 외부 인터페이스는 `snake_case`
- 요청 body / params / response json 모두 최종 컬럼명 기준으로 맞춤
- 예전 응답 키가 프론트와 연결되어 있으면 TODO 또는 변경 메모 남길 것

## 코드 수정 방식
- 단순 검색치환 금지
- 현재 코드에서 이미 맞는 부분은 유지
- 최종 명세와 불일치하는 부분만 수정
- import / export / middleware / route 연결 / SQL alias / response key를 함께 점검

# 코덱스 작업 지침

코덱스는 이 파일을 최종 기준으로 사용해야 한다.

## 해야 할 일
1. 현재 코드와 이 명세를 비교
2. 이미 맞는 부분은 유지
3. 불일치하는 부분만 수정
4. 파일별 전체 수정본 제시
5. 프론트와 함께 수정해야 하는 키는 따로 표시

## 하지 말아야 할 일
- 전체 재작성
- 이미 맞는 activity 구조를 다시 건드리기
- `sche_id`를 `schedule_id`로 되돌리기
- PDF/최종 명세와 다른 예전 초안 기준으로 수정하기

# 최종 체크 포인트

아래 항목이 코드에 남아 있으면 반드시 검토:
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

## 테이블 생성 쿼리문


CREATE TABLE public.members (
mem_id serial4 NOT NULL,
social_id varchar(100) NOT NULL,
provider varchar(20) NOT NULL,
email varchar(100) NOT NULL,
nick varchar(50) NOT NULL,
profile_img text NOT NULL,
fcm_token text NULL,
joined_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
CONSTRAINT members_pkey PRIMARY KEY (mem_id)
);
CREATE INDEX ix_members_1 ON public.members USING btree (joined_at);
CREATE UNIQUE INDEX uq_members_1 ON public.members USING btree (email, nick);
-- 기존 DB 마이그레이션: ALTER TABLE public.members ADD COLUMN IF NOT EXISTS fcm_token text NULL;

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
fingerprint_id int4 NOT NULL,
guardian_name varchar(100) NOT NULL,
guardian_phone varchar(20) NOT NULL,
created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_at timestamptz NULL,
deleted_at timestamptz NULL,
CONSTRAINT patients_pkey PRIMARY KEY (patient_id),
CONSTRAINT fk_patients_mem_id_members_mem_id FOREIGN KEY (mem_id) REFERENCES
public.members(mem_id)
);

CREATE TABLE public.devices (
device_id serial4 NOT NULL,
device_uid varchar(100) NOT NULL,
patient_id int4 NOT NULL,
device_status varchar(50) NOT NULL,
last_ping timestamptz NULL,
registered_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
CONSTRAINT devices_pkey PRIMARY KEY (device_id),
CONSTRAINT fk_devices_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES
public.patients(patient_id)
);


CREATE INDEX ix_devices_1 ON public.devices USING btree (registered_at);
CREATE TABLE public.medications (
medi_id serial4 NOT NULL,
item_seq varchar(50) NOT NULL,
medi_name varchar(255) NOT NULL,
CONSTRAINT medications_pkey PRIMARY KEY (medi_id)
);
CREATE INDEX idx_medi_name_trgm ON public.medications USING gin (medi_name gin_trgm_ops);

CREATE TABLE public.schedules (
sche_id serial4 NOT NULL,
patient_id int4 NOT NULL,
medi_id int4 NOT NULL,
start_date date NOT NULL,
end_date date,
time_to_take time NOT NULL,
dose_interval int4,
status varchar(20) NOT NULL,
created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_at timestamptz,
CONSTRAINT schedules_pkey PRIMARY KEY (sche_id),
CONSTRAINT fk_schedules_medi_id_medications_medi_id FOREIGN KEY (medi_id) REFERENCES
public.medications(medi_id),
CONSTRAINT fk_schedules_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES
public.patients(patient_id)
);
CREATE INDEX ix_schedules_1 ON public.schedules USING btree (created_at);

CREATE TABLE public.face_embeddings (
face_id serial4 NOT NULL,
patient_id int4 NOT NULL,
face_vector public.vector NOT NULL,
created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
CONSTRAINT face_embeddings_pkey PRIMARY KEY (face_id),
CONSTRAINT fk_face_embeddings_patient_id_patients_patient_id FOREIGN KEY (patient_id)
REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_face_embeddings_1 ON public.face_embeddings USING btree (created_at);
CREATE INDEX ix_face_embeddings_2 ON public.face_embeddings USING btree (face_vector);
CREATE INDEX ix_face_embeddings_3 ON public.face_embeddings USING btree (patient_id);

CREATE TABLE public.activities (
activity_id serial4 NOT NULL,
patient_id int4 NOT NULL,
sche_id int4 NOT NULL,
sche_time timestamptz NOT NULL,
actual_time timestamptz NULL,
status varchar(20) NOT NULL,
is_face_auth bool NOT NULL,
is_ai_check bool NOT NULL,
similarity_score numeric(5, 4) NOT NULL,
created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
CONSTRAINT activities_pkey PRIMARY KEY (activity_id),
CONSTRAINT fk_activities_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES
public.patients(patient_id),
CONSTRAINT fk_activities_sche_id_schedules_sche_id FOREIGN KEY (sche_id) REFERENCES
public.schedules(sche_id)
);
CREATE INDEX ix_activities_1 ON public.activities USING btree (created_at);
CREATE INDEX ix_activities_2 ON public.activities USING btree (patient_id, sche_time);

CREATE TABLE public.notifications (
noti_id serial4 NOT NULL,
mem_id int4 NOT NULL,
patient_id int4 NOT NULL,
activity_id int4 NOT NULL,
noti_title varchar(255) NOT NULL,
noti_msg text NOT NULL,
created_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
is_received bool NOT NULL,
received_time timestamptz NULL,
noti_type varchar(50) NOT NULL,
CONSTRAINT notifications_pkey PRIMARY KEY (noti_id),
CONSTRAINT fk_notifications_activity_id_activities_activity_id FOREIGN KEY (activity_id) REFERENCES
public.activities(activity_id),
CONSTRAINT fk_notifications_mem_id_members_mem_id FOREIGN KEY (mem_id) REFERENCES
public.members(mem_id),
CONSTRAINT fk_notifications_patient_id_patients_patient_id FOREIGN KEY (patient_id) REFERENCES
public.patients(patient_id)
);
CREATE INDEX ix_notifications_1 ON public.notifications USING btree (created_at);
CREATE INDEX ix_notifications_2 ON public.notifications USING btree (mem_id, is_received);

CREATE TABLE public.voice_samples (
voice_id serial4 NOT NULL,
patient_id int4 NOT NULL,
file_name varchar(255) NOT NULL,
file_path text NOT NULL,
file_size int4 NULL,
mime_type varchar(100) NULL,
status varchar(20) NOT NULL DEFAULT 'pending',
uploaded_at timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_at timestamptz NULL,
CONSTRAINT voice_samples_pkey PRIMARY KEY (voice_id),
CONSTRAINT fk_voice_samples_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_voice_samples_1 ON public.voice_samples USING btree (patient_id);
CREATE INDEX ix_voice_samples_2 ON public.voice_samples USING btree (uploaded_at);

CREATE TABLE public.fingerprints (
fp_id serial4 NOT NULL,
patient_id int4 NOT NULL,
slot_id int4 NOT NULL,
label varchar(50) NOT NULL DEFAULT '지문',
registered_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT fingerprints_pkey PRIMARY KEY (fp_id),
CONSTRAINT fingerprints_patient_slot_unique UNIQUE (patient_id, slot_id),
CONSTRAINT fk_fingerprints_patient_id FOREIGN KEY (patient_id) REFERENCES public.patients(patient_id)
);
CREATE INDEX ix_fingerprints_1 ON public.fingerprints USING btree (patient_id);

