# Care-full Server API Specification

## 1. 전체 API 목록 요약

| Method | Endpoint | 설명 | 인증 |
|--------|----------|------|------|
| GET | `/api/user/callback` | 카카오 OAuth 콜백 로그인 | X |
| GET | `/api/user/google/callback` | 구글 OAuth 콜백 로그인 | X |
| GET | `/api/user/naver/callback` | 네이버 OAuth 콜백 로그인 | X |
| POST | `/api/user/dev-login` | 개발용 mock 로그인 | X |
| POST | `/api/user/register-patient` | 회원 기준 환자+기기 등록 | O |
| POST | `/api/patient/register` | 환자 정보 등록 | O |
| GET | `/api/patient/me` | 내 환자 정보 조회 | O |
| PUT | `/api/patient/me` | 내 환자 정보 수정 | O |
| GET | `/api/medication` | 약 사전 전체 조회 | X |
| GET | `/api/medication/search` | 약 이름 검색 | X |
| POST | `/api/schedule` | 복약 일정 등록 | O |
| GET | `/api/schedule` | 내 복약 일정 목록 조회 | O |
| PUT | `/api/schedule/:id` | 내 복약 일정 수정 | O |
| DELETE | `/api/schedule/:id` | 내 복약 일정 삭제 | O |
| GET | `/api/dashboard` | 로그인 사용자 대시보드 조회 | O |
| POST | `/api/device/register` | 내 계정에 기기 연결 | O |
| GET | `/api/device/me` | 내 기기 조회 | O |
| DELETE | `/api/device/me` | 내 기기 연결 해제 | O |
| POST | `/api/face-data` | 얼굴 임베딩 저장 | O |
| GET | `/api/face-data` | 얼굴 임베딩 목록 조회 | O |
| POST | `/api/log` | 복약 로그 저장 | O |
| GET | `/api/log` | 내 복약 로그 조회 | O |
| GET | `/api/notification` | 내 알림 목록 조회 | O |
| PATCH | `/api/notification/read-all` | 내 알림 전체 읽음 처리 | O |
| PATCH | `/api/notification/:id/read` | 내 알림 1건 읽음 처리 | O |

## 2. API 상세 명세

### 공통 인증/응답 규칙

- 인증 미들웨어: `middleware/auth.js`
- 인증 방식: `Authorization: Bearer <JWT>`
- 인증 성공 시: `req.user.memberId` 사용
- `memberId -> user_id` 변환: `utils/auth-user.js`
- 공통 응답 헬퍼:
  - `sendSuccess(res, statusCode, payload)` -> `{ success: true, ...payload }`
  - `sendError(res, statusCode, message, extra)` -> `{ success: false, message, ...extra }`
- 예외:
  - `user.js`, `device.js`, `medication.js`는 일부/전체가 `sendSuccess/sendError` 미사용
- 숫자 검증 유틸:
  - `parseNumericValue(value)`
  - `parseNumericFields(body, fields)`
  - `validateRequiredFields(body, requiredFields)`

---

### [GET] `/api/user/callback`

설명: 카카오 OAuth code로 로그인/회원 생성 후 JWT 발급  
인증: 불필요  
req.user.memberId 사용: X

Request

- query:
  - `code` 필수

Response

```json
{
  "success": true,
  "token": "jwt",
  "isNewUser": true,
  "nextStep": "/register-patient",
  "userData": {
    "memberId": 1,
    "nickname": "홍길동",
    "provider": "kakao"
  }
}
```

DB 사용

- `members`

비고

- 카카오 API 호출 후 `members(social_id, provider)`로 회원 조회/생성

---

### [GET] `/api/user/google/callback`

설명: 구글 OAuth code 로그인  
인증: 불필요  
req.user.memberId 사용: X

Request

- query:
  - `code` 필수

Response

- 카카오와 동일 구조
- `provider: "google"`

DB 사용

- `members`

---

### [GET] `/api/user/naver/callback`

설명: 네이버 OAuth code 로그인  
인증: 불필요  
req.user.memberId 사용: X

Request

- query:
  - `code` 필수
  - `state` 필수

Response

- 동일 구조
- `provider: "naver"`

DB 사용

- `members`

---

### [POST] `/api/user/dev-login`

설명: 개발용 mock 로그인  
인증: 불필요  
req.user.memberId 사용: X

Request

- body:
  - `social_id` 필수
  - `provider` 필수
  - `nickname` 필수
  - `email` 선택

Response

- 소셜 로그인과 동일 구조

DB 사용

- `members`

비고

- 실제 OAuth 없이 테스트 가능

---

### [POST] `/api/user/register-patient`

설명: JWT 로그인 회원 기준으로 `users` 생성 후 `devices` 연결  
인증: 필요 (`verifyToken`)  
req.user.memberId 사용: O

Request

- headers:
  - `Authorization`
- body:
  - `name`
  - `birth_date`
  - `gender`
  - `blood_type`
  - `height`
  - `weight`
  - `serial_number`
- 코드상 명시적 필수 검증은 없음

Response

```json
{
  "success": true,
  "message": "환자 및 기기 등록 완료",
  "userId": 3
}
```

DB 사용

- `users`
- `devices`

비고

- transaction 사용
- `patient/register`와 기능 중복 성격 있음

---

### [POST] `/api/patient/register`

설명: 환자 정보 등록  
인증: 필요  
req.user.memberId 사용: O

Request

- body 필수:
  - `name`
  - `birth_date`
  - `gender`
  - `phone_number`
  - `address`
  - `blood_type`
  - `height`
  - `weight`
  - `fingerprint_id`
  - `emergency_contact_name`
  - `emergency_contact_phone`

Response

```json
{
  "success": true,
  "message": "환자 정보가 등록되었습니다.",
  "patient": {
    "user_id": 1,
    "member_id": 10,
    "name": "홍길동"
  }
}
```

DB 사용

- `users`

비고

- 동일 `member_id` 존재 시 409
- 동일 `fingerprint_id` 존재 시 409

---

### [GET] `/api/patient/me`

설명: 내 환자 정보 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "patient": {
    "user_id": 1,
    "member_id": 10,
    "name": "홍길동",
    "birth_date": "2000-01-01",
    "gender": "M"
  }
}
```

DB 사용

- `users`

---

### [PUT] `/api/patient/me`

설명: 내 환자 정보 수정  
인증: 필요  
req.user.memberId 사용: O

Request

- body: `POST /api/patient/register`와 동일 필수 구조

Response

```json
{
  "success": true,
  "message": "환자 정보가 수정되었습니다.",
  "patient": { "...": "..." }
}
```

DB 사용

- `users`

---

### [GET] `/api/medication`

설명: 약 사전 전체 조회  
인증: 불필요  
req.user.memberId 사용: X

Request

- 없음

Response

```json
{
  "success": true,
  "data": [
    {
      "medication_id": 1,
      "item_seq": "20240101",
      "name": "타이레놀"
    }
  ]
}
```

DB 사용

- `medications`

비고

- `sendSuccess` 미사용

---

### [GET] `/api/medication/search`

설명: 약 이름 검색  
인증: 불필요  
req.user.memberId 사용: X

Request

- query:
  - `keyword` 필수

Response

```json
{
  "success": true,
  "data": [
    {
      "medication_id": 1,
      "item_seq": "20240101",
      "name": "타이레놀"
    }
  ]
}
```

DB 사용

- `medications`

비고

- `keyword` 없으면 400
- `sendSuccess` 미사용

---

### [POST] `/api/schedule`

설명: 복약 일정 등록  
인증: 필요  
req.user.memberId 사용: O

Request

- body 필수:
  - `medication_id`
  - `dosage_count`
  - `scheduled_time`
  - `start_date`
  - `end_date`
  - `days_of_week`
  - `repeat_interval`
  - `status`

Response

```json
{
  "success": true,
  "message": "복약 일정이 등록되었습니다.",
  "schedule": {
    "schedule_id": 1,
    "user_id": 3,
    "medication_id": 10,
    "dosage_count": 1,
    "scheduled_time": "08:00:00"
  }
}
```

DB 사용

- `users`
- `schedules`

비고

- 내부적으로 `findUserIdByMemberId()` 사용

---

### [GET] `/api/schedule`

설명: 내 복약 일정 목록 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "schedules": [
    {
      "schedule_id": 1,
      "user_id": 3,
      "medication_id": 10,
      "dosage_count": 1,
      "scheduled_time": "08:00:00",
      "days_of_week": [1, 3, 5]
    }
  ]
}
```

DB 사용

- `users`
- `schedules`

---

### [PUT] `/api/schedule/:id`

설명: 내 복약 일정 수정  
인증: 필요  
req.user.memberId 사용: O

Request

- params:
  - `id` 숫자 필수
- body:
  - `POST /api/schedule`와 동일 필수 구조

Response

```json
{
  "success": true,
  "message": "복약 일정이 수정되었습니다.",
  "schedule": { "...": "..." }
}
```

DB 사용

- `users`
- `schedules`

---

### [DELETE] `/api/schedule/:id`

설명: 내 복약 일정 삭제  
인증: 필요  
req.user.memberId 사용: O

Request

- params:
  - `id` 숫자 필수

Response

```json
{
  "success": true,
  "message": "복약 일정이 삭제되었습니다.",
  "schedule": { "...": "..." }
}
```

DB 사용

- `users`
- `schedules`

---

### [GET] `/api/dashboard`

설명: 로그인 사용자 기준 대시보드 통합 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "message": "대시보드 조회 성공",
  "data": {
    "summary": {
      "todaySuccessRate": 67,
      "todayTotalScheduledCount": 3,
      "todayCompletedCount": 2,
      "todayMissedCount": 1
    },
    "device": {
      "isConnected": true,
      "deviceId": 1,
      "serialNumber": "CAREFULL-0003",
      "deviceStatus": "REGISTERED",
      "fillLevel": null,
      "remainingCount": null,
      "lastSyncAt": "2026-04-13T08:00:00.000Z",
      "nextScheduledTime": "21:00:00"
    },
    "todaySchedules": [],
    "recentNotifications": [],
    "recentLogs": []
  }
}
```

DB 사용

- `users`
- `schedules`
- `logs`
- `notifications`
- `devices`
- `medications`

비고

- `days_of_week`가 `ANY(array)` 구조라 PostgreSQL 배열 컬럼 전제
- `fillLevel`, `remainingCount`는 코드상 `null` 고정

---

### [POST] `/api/device/register`

설명: 내 계정에 시리얼 번호 기기 연결  
인증: 필요  
req.user.memberId 사용: O

Request

- body:
  - `serial_number` 필수

Response

```json
{
  "success": true,
  "message": "기기 등록이 완료되었습니다.",
  "device": {
    "device_id": 1,
    "serial_number": "CAREFULL-0003",
    "user_id": 3,
    "status": "REGISTERED"
  }
}
```

DB 사용

- `users`
- `devices`

비고

- `sendSuccess/sendError` 미사용
- 라우터 내부에서 `findUserIdByMemberId`를 중복 구현

---

### [GET] `/api/device/me`

설명: 내 계정에 연결된 기기 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "device": {
    "device_id": 1,
    "serial_number": "CAREFULL-0003",
    "status": "REGISTERED",
    "last_ping": "2026-04-13T08:00:00.000Z"
  }
}
```

DB 사용

- `users`
- `devices`

비고

- `sendSuccess/sendError` 미사용

---

### [DELETE] `/api/device/me`

설명: 내 기기 연결 해제  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "message": "기기 연결이 해제되었습니다.",
  "device": {
    "device_id": 1,
    "serial_number": "CAREFULL-0003",
    "user_id": null,
    "status": "UNREGISTERED"
  }
}
```

DB 사용

- `users`
- `devices`

---

### [POST] `/api/face-data`

설명: 얼굴 임베딩 저장  
인증: 필요  
req.user.memberId 사용: O

Request

- body:
  - `embedding` 필수 배열

```json
{
  "embedding": [0.12, -0.03, 0.44]
}
```

Response

```json
{
  "success": true,
  "message": "얼굴 데이터가 저장되었습니다.",
  "face_data": {
    "face_id": 1,
    "user_id": 3,
    "embedding": "[0.12,-0.03,0.44]",
    "created_at": "2026-04-13T01:00:00.000Z"
  }
}
```

DB 사용

- `users`
- `face_data`

비고

- 코드상 `VECTOR(128)` 전제
- 배열을 문자열 `"[...]"` 형태로 변환해 저장

---

### [GET] `/api/face-data`

설명: 내 얼굴 임베딩 목록 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "face_data": [
    {
      "face_id": 1,
      "user_id": 3,
      "embedding": "[0.12,-0.03,0.44]",
      "created_at": "2026-04-13T01:00:00.000Z"
    }
  ]
}
```

DB 사용

- `users`
- `face_data`

---

### [POST] `/api/log`

설명: 복약 로그 저장, 성공 시 알림도 생성 가능  
인증: 필요  
req.user.memberId 사용: O

Request

- body 필수:
  - `schedule_id` 숫자
  - `planned_time`
  - `status`
- body 선택:
  - `actual_time`
  - `face_auth_result`
  - `action_auth_result`
  - `similarity_score` 숫자
- 허용 status:
  - `SUCCESS`
  - `FAILED`
  - `MISSED`

Response

```json
{
  "success": true,
  "message": "복약 로그가 저장되었습니다.",
  "log": {
    "log_id": 1,
    "user_id": 3,
    "schedule_id": 10,
    "planned_time": "2026-04-13T08:00:00.000Z",
    "actual_time": "2026-04-13T08:01:00.000Z",
    "status": "SUCCESS",
    "face_auth_result": true,
    "action_auth_result": true,
    "similarity_score": 0.93
  },
  "notification": {
    "notification_id": 20,
    "member_id": 5,
    "log_id": 1,
    "title": "복약 완료 알림",
    "type": "SUCCESS"
  }
}
```

DB 사용

- `users`
- `schedules`
- `logs`
- `notifications`
- `medications`

비고

- transaction 사용
- `SUCCESS`일 때만 성공 알림 생성

---

### [GET] `/api/log`

설명: 내 복약 로그 목록 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "logs": [
    {
      "log_id": 1,
      "user_id": 3,
      "schedule_id": 10,
      "planned_time": "2026-04-13T08:00:00.000Z",
      "actual_time": "2026-04-13T08:01:00.000Z",
      "status": "SUCCESS",
      "face_auth_result": true,
      "action_auth_result": true,
      "similarity_score": 0.93,
      "created_at": "2026-04-13T08:01:00.000Z"
    }
  ]
}
```

DB 사용

- `users`
- `logs`

---

### [GET] `/api/notification`

설명: 내 알림 목록 조회  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "notifications": [
    {
      "notification_id": 1,
      "member_id": 5,
      "log_id": 10,
      "title": "복약 실패 알림",
      "message": "복약 기록이 없습니다.",
      "is_read": false,
      "type": "MISSED",
      "created_at": "2026-04-13T08:30:00.000Z"
    }
  ]
}
```

DB 사용

- `notifications`

---

### [PATCH] `/api/notification/read-all`

설명: 내 알림 전체 읽음 처리  
인증: 필요  
req.user.memberId 사용: O

Request

- headers: `Authorization`

Response

```json
{
  "success": true,
  "message": "전체 알림이 읽음 처리되었습니다.",
  "count": 5
}
```

DB 사용

- `notifications`

---

### [PATCH] `/api/notification/:id/read`

설명: 내 알림 1건 읽음 처리  
인증: 필요  
req.user.memberId 사용: O

Request

- params:
  - `id` 숫자 필수

Response

```json
{
  "success": true,
  "message": "알림이 읽음 처리되었습니다.",
  "notification": {
    "notification_id": 1,
    "member_id": 5,
    "log_id": 10,
    "title": "복약 실패 알림",
    "message": "복약 기록이 없습니다.",
    "is_read": true,
    "type": "MISSED",
    "created_at": "2026-04-13T08:30:00.000Z"
  }
}
```

DB 사용

- `notifications`

## 3. 문제 있는 API / 구조 분석

### 인증 없는 API

- `/api/user/callback`
- `/api/user/google/callback`
- `/api/user/naver/callback`
- `/api/user/dev-login`
- `/api/medication`
- `/api/medication/search`

평가

- OAuth 콜백/로그인은 인증 없는 게 정상
- `medication` 공개 조회는 의도일 수 있지만, 내부 사전 API라면 인증 정책 재검토 가능

### 구조가 다른 API

- `user.js`, `device.js`, `medication.js`는 `sendSuccess/sendError`를 사용하지 않고 직접 `res.status().json()` 사용
- `patient.js`, `schedule.js`, `log.js`, `notification.js`, `dashboard.js`, `face-data.js`는 공통 헬퍼 사용

영향

- 프론트가 응답 파싱 규칙을 API별로 다르게 가져가야 할 수 있음

### deprecated / 구버전 느낌

- `routes/user.js`의 `/api/user/register-patient`
  - 환자 생성 + 기기 등록을 한 번에 처리
  - `routes/patient.js`, `routes/device.js`와 역할이 겹침
- `public/index.html`은 아직 `/api/medication/schedule`, `/api/medication/log`를 호출
  - 실제 라우터에는 없음
  - 테스트 페이지와 서버 API가 불일치

### 중복 / 비효율 구조

- `device.js` 내부에 `findUserIdByMemberId`가 중복 정의
  - 이미 `utils/auth-user.js` 존재
- 사용자 식별 흐름은 대체로 `memberId -> user_id`로 정리됐지만,
  - `notifications`는 `member_id`
  - 다른 도메인은 `user_id`
  - 테이블별 기준 키가 혼재
- `user/register-patient`와 `patient/register`가 둘 다 `users` 생성 관여
  - 등록 플로우가 두 갈래

### 누락된 API

- 현재 코드 기준 “없는 API”인데 프론트 테스트 페이지가 기대하는 것
  - `GET /api/medication/schedule`
  - `POST /api/medication/log`
- 화면설계서 기준 가능성 있는 추가 필요 API
  - 대시보드 상세 카드용 디바이스 상태 갱신 API
  - 약통 잔량 갱신 API
  - 최근 기록 페이징 API
- 다만 위 3개는 코드에 없으므로 “추정”입니다.

## 4. 구조 개선 제안

- 경로 리소스명 통일
  - 현재 `schedule`, `log`, `notification`, `face-data`가 단수형
  - REST 관점에서는 `/api/schedules`, `/api/logs`, `/api/notifications`, `/api/face-data`처럼 복수형이 더 일관적
- 응답 형식 통일
  - 전 라우터에 `sendSuccess/sendError` 적용
  - 성공 시 `message` 유무도 통일
- 등록 플로우 정리
  - `POST /api/user/register-patient`와 `POST /api/patient/register` 중 하나를 주 플로우로 정리
- 공통 유틸 재사용
  - `device.js`도 `utils/auth-user.js` 사용
- 스키마 키 전략 문서화
  - `members.member_id`
  - `users.user_id`
  - `notifications.member_id`
  - 그 외 대부분 `user_id`
- 테스트 페이지 정리
  - `index.html`에서 없는 API 호출 제거 또는 실제 구현 추가

## 5. DB 연관성 요약

- `members`
  - 소셜 로그인 회원
  - `user.js`
- `users`
  - 환자/실사용자 정보
  - `user.js`, `patient.js`, `schedule.js`, `device.js`, `log.js`, `dashboard.js`, `face-data.js`
- `devices`
  - 기기 연결 상태
  - `user.js`, `device.js`, `dashboard.js`
- `medications`
  - 약 사전
  - `medication.js`, `log.js`, `dashboard.js`
- `schedules`
  - 복약 일정
  - `schedule.js`, `log.js`, `dashboard.js`, `missed-log-job.js`
- `logs`
  - 복약 결과
  - `log.js`, `dashboard.js`, `missed-log-job.js`
- `notifications`
  - 알림
  - `notification.js`, `log.js`, `dashboard.js`, `missed-log-job.js`
- `face_data`
  - 얼굴 임베딩
  - `face-data.js`

## 6. 프론트엔드용 핵심 사용 포인트

- 로그인 완료 후 저장해야 하는 값은 `token`
- 인증 API 대부분은 `Authorization: Bearer <token>` 필수
- 복약 관련 핵심 화면 흐름은 보통 아래 순서
  1. `/api/user/dev-login` 또는 소셜 콜백 로그인
  2. `/api/patient/register` 또는 `/api/user/register-patient`
  3. `/api/device/register`
  4. `/api/schedule`
  5. `/api/log`
  6. `/api/dashboard`
  7. `/api/notification`
