# Care-full Front API Spec

프론트 전달용 요약 문서입니다.  
백엔드 내부 구조, DB 상세, 개선 제안은 제외하고 실제 호출에 필요한 정보만 정리했습니다.

## 1. 공통 규칙

### Base
- 서버 기준 모든 API는 `/api/...` 경로 사용

### 인증
- 인증 필요한 API는 헤더에 아래 형식 필요

```http
Authorization: Bearer {token}
```

### 공통 응답
- 대부분 아래 구조를 사용합니다.

```json
{
  "success": true
}
```

- 다만 일부 API는 `message`, `data`, `patient`, `device`, `schedule` 등 키가 조금씩 다릅니다.
- 프론트에서는 각 API별 응답 예시를 기준으로 파싱하는 것이 안전합니다.

### 로그인 후 저장할 값
- `token`

---

## 2. 먼저 써야 하는 핵심 API

일반적인 프론트 사용 순서:

1. 로그인
2. 환자 등록 또는 환자 정보 조회
3. 기기 등록
4. 일정 등록/조회
5. 복약 로그 저장/조회
6. 대시보드 조회
7. 알림 조회/읽음 처리

---

## 3. API 요약 목록

| Method | Endpoint | 인증 | 용도 |
|--------|----------|------|------|
| POST | `/api/user/dev-login` | X | 개발용 로그인 |
| GET | `/api/user/callback` | X | 카카오 로그인 콜백 |
| GET | `/api/user/google/callback` | X | 구글 로그인 콜백 |
| GET | `/api/user/naver/callback` | X | 네이버 로그인 콜백 |
| POST | `/api/patient/register` | O | 환자 정보 등록 |
| GET | `/api/patient/me` | O | 내 환자 정보 조회 |
| PUT | `/api/patient/me` | O | 내 환자 정보 수정 |
| POST | `/api/device/register` | O | 기기 연결 |
| GET | `/api/device/me` | O | 내 기기 조회 |
| DELETE | `/api/device/me` | O | 기기 연결 해제 |
| GET | `/api/medication` | X | 약 목록 조회 |
| GET | `/api/medication/search?keyword=` | X | 약 검색 |
| POST | `/api/schedule` | O | 일정 등록 |
| GET | `/api/schedule` | O | 일정 목록 조회 |
| PUT | `/api/schedule/:id` | O | 일정 수정 |
| DELETE | `/api/schedule/:id` | O | 일정 삭제 |
| POST | `/api/log` | O | 복약 로그 저장 |
| GET | `/api/log` | O | 복약 로그 목록 조회 |
| GET | `/api/dashboard` | O | 대시보드 조회 |
| GET | `/api/notification` | O | 알림 목록 조회 |
| PATCH | `/api/notification/:id/read` | O | 알림 1건 읽음 처리 |
| PATCH | `/api/notification/read-all` | O | 알림 전체 읽음 처리 |
| POST | `/api/face-data` | O | 얼굴 임베딩 저장 |
| GET | `/api/face-data` | O | 얼굴 임베딩 목록 조회 |

---

## 4. 상세 명세

### 4-1. 로그인

### [POST] `/api/user/dev-login`
개발용 로그인

Request
```json
{
  "social_id": "test-user-001",
  "provider": "mock",
  "nickname": "테스트유저",
  "email": "test@example.com"
}
```

Response
```json
{
  "success": true,
  "token": "jwt",
  "isNewUser": true,
  "nextStep": "/register-patient",
  "userData": {
    "memberId": 1,
    "nickname": "테스트유저",
    "provider": "mock"
  }
}
```

프론트 메모
- 로그인 후 `token` 저장 필수

---

### [GET] `/api/user/callback`
카카오 로그인 콜백

Query
- `code`

Response
- `dev-login`과 유사

---

### [GET] `/api/user/google/callback`
구글 로그인 콜백

Query
- `code`

---

### [GET] `/api/user/naver/callback`
네이버 로그인 콜백

Query
- `code`
- `state`

---

## 4-2. 환자

### [POST] `/api/patient/register`
환자 정보 등록

Request
```json
{
  "name": "홍길동",
  "birth_date": "2000-01-01",
  "gender": "M",
  "phone_number": "010-1234-5678",
  "address": "서울시 ...",
  "blood_type": "A+",
  "height": 175,
  "weight": 70,
  "fingerprint_id": 1,
  "emergency_contact_name": "보호자",
  "emergency_contact_phone": "010-9999-9999"
}
```

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

---

### [GET] `/api/patient/me`
내 환자 정보 조회

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

---

### [PUT] `/api/patient/me`
내 환자 정보 수정

Request
- `POST /api/patient/register`와 동일

Response
```json
{
  "success": true,
  "message": "환자 정보가 수정되었습니다.",
  "patient": {
    "user_id": 1
  }
}
```

---

## 4-3. 기기

### [POST] `/api/device/register`
기기 연결

Request
```json
{
  "serial_number": "CAREFULL-0003"
}
```

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

---

### [GET] `/api/device/me`
내 기기 조회

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

---

### [DELETE] `/api/device/me`
내 기기 연결 해제

Response
```json
{
  "success": true,
  "message": "기기 연결이 해제되었습니다.",
  "device": {
    "device_id": 1,
    "status": "UNREGISTERED"
  }
}
```

---

## 4-4. 약 조회

### [GET] `/api/medication`
약 전체 조회

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

---

### [GET] `/api/medication/search?keyword=타이`
약 검색

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

---

## 4-5. 복약 일정

### [POST] `/api/schedule`
복약 일정 등록

Request
```json
{
  "medication_id": 1,
  "dosage_count": 1,
  "scheduled_time": "08:00:00",
  "start_date": "2026-04-13",
  "end_date": "2026-04-30",
  "days_of_week": [1, 3, 5],
  "repeat_interval": 1,
  "status": "ACTIVE"
}
```

Response
```json
{
  "success": true,
  "message": "복약 일정이 등록되었습니다.",
  "schedule": {
    "schedule_id": 1,
    "user_id": 3,
    "medication_id": 1
  }
}
```

---

### [GET] `/api/schedule`
내 일정 목록 조회

Response
```json
{
  "success": true,
  "schedules": [
    {
      "schedule_id": 1,
      "user_id": 3,
      "medication_id": 1,
      "dosage_count": 1,
      "scheduled_time": "08:00:00",
      "days_of_week": [1, 3, 5],
      "status": "ACTIVE"
    }
  ]
}
```

---

### [PUT] `/api/schedule/:id`
일정 수정

Request
- path param: `id`
- body: 일정 등록과 동일

---

### [DELETE] `/api/schedule/:id`
일정 삭제

Request
- path param: `id`

---

## 4-6. 복약 로그

### [POST] `/api/log`
복약 로그 저장

Request
```json
{
  "schedule_id": 1,
  "planned_time": "2026-04-14T08:00:00+09:00",
  "actual_time": "2026-04-14T08:03:12+09:00",
  "status": "SUCCESS",
  "face_auth_result": true,
  "action_auth_result": true,
  "similarity_score": 0.9321
}
```

허용 status
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
    "schedule_id": 1,
    "status": "SUCCESS"
  },
  "notification": {
    "notification_id": 20,
    "type": "SUCCESS"
  }
}
```

프론트 메모
- `SUCCESS` 저장 시 완료 알림이 같이 생성될 수 있음

---

### [GET] `/api/log`
내 복약 로그 조회

Response
```json
{
  "success": true,
  "logs": [
    {
      "log_id": 1,
      "user_id": 3,
      "schedule_id": 1,
      "planned_time": "2026-04-13T08:00:00.000Z",
      "actual_time": "2026-04-13T08:01:00.000Z",
      "status": "SUCCESS",
      "created_at": "2026-04-13T08:01:00.000Z"
    }
  ]
}
```

---

## 4-7. 대시보드

### [GET] `/api/dashboard`
대시보드 첫 화면 데이터 조회

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

프론트 메모
- 기기 잔량/채움률 관련 값은 현재 `null` 가능
- 오늘 일정, 최근 알림, 최근 로그를 한 번에 받음

---

## 4-8. 알림

### [GET] `/api/notification`
알림 목록 조회

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

---

### [PATCH] `/api/notification/:id/read`
알림 1건 읽음 처리

Request
- path param: `id`

Response
```json
{
  "success": true,
  "message": "알림이 읽음 처리되었습니다.",
  "notification": {
    "notification_id": 1,
    "is_read": true
  }
}
```

---

### [PATCH] `/api/notification/read-all`
알림 전체 읽음 처리

Response
```json
{
  "success": true,
  "message": "전체 알림이 읽음 처리되었습니다.",
  "count": 5
}
```

---

## 4-9. 얼굴 데이터

### [POST] `/api/face-data`
얼굴 임베딩 저장

Request
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

---

### [GET] `/api/face-data`
얼굴 데이터 목록 조회

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

---

## 5. 프론트 주의사항

### 현재 사용 가능
- 로그인
- 환자 등록/조회/수정
- 기기 등록/조회/해제
- 일정 등록/조회/수정/삭제
- 로그 저장/조회
- 대시보드 조회
- 알림 조회/읽음 처리
- 얼굴 데이터 저장/조회

### 현재 주의 필요
- 응답 구조가 API마다 조금씩 다름
- `device.js`, `user.js`, `medication.js`는 응답 형식이 다른 라우터보다 덜 통일됨
- `days_of_week` 형식은 현재 코드 기준 배열 형태 사용 권장

### 현재 없는 API
- `GET /api/medication/schedule`
- `POST /api/medication/log`

프론트 메모
- 테스트용 `index.html`에는 위 두 API 버튼이 남아 있을 수 있지만 실제 서버 라우터에는 없음
- 프론트에서는 이 경로 사용하면 안 됨

---

## 6. 프론트 추천 사용 흐름 예시

1. `POST /api/user/dev-login`
2. `POST /api/patient/register`
3. `POST /api/device/register`
4. `GET /api/medication`
5. `POST /api/schedule`
6. `GET /api/dashboard`
7. `POST /api/log`
8. `GET /api/notification`
