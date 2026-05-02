# CARE-FULL 시스템 설계 기준서 (AI 작업용 - FINAL + ENV)

---

## 0. 환경 구성 기준 (필수)

본 프로젝트는 **로컬 개발 환경 + AWS 배포 환경(duckdns/duks)**을 병행한다.
모든 코드는 **두 환경 모두에서 동일하게 동작해야 한다.**

---

## 0.1 로컬 개발 환경

```env
SSL_KEY_PATH=192.168.219.225.nip.io-key.pem
SSL_CERT_PATH=192.168.219.225.nip.io.pem

ALLOWED_ORIGINS=https://192.168.219.225.nip.io:5173
FRONTEND_URL=https://192.168.219.225.nip.io:5173

VITE_API_BASE_URL=https://192.168.219.225.nip.io
```

특징:

```text
- Vite dev server (https)
- nip.io 도메인 사용
- self-signed 인증서 사용
- 로컬 네트워크 기반 테스트
```

---

## 0.2 배포 환경 (AWS / duckdns)

```env
VITE_API_BASE_URL=https://carefulllion.duckdns.org

ALLOWED_ORIGINS=https://carefull-zeta.vercel.app
FRONTEND_URL=https://carefull-zeta.vercel.app
```

특징:

```text
- frontend: build 후 정적 배포 (Vercel)
- backend: AWS 서버 (Node.js)
- HTTPS는 서버 또는 플랫폼에서 처리
- 로컬 인증서 파일 없음
```

---

## 0.3 환경 분리 절대 규칙

❌ 금지:

```text
- localhost / 192.168.x.x 하드코딩
- vite.config.js에 인증서 경로 하드코딩
- 환경별 if 분기 코드 남발
- API URL 직접 문자열 작성
```

✔ 필수:

```text
- 모든 URL은 .env로 관리
- API_BASE_URL 반드시 사용
- FRONTEND_URL 반드시 사용
- ALLOWED_ORIGINS 반드시 사용
```

---

## 0.4 CORS / URL 기준

```text
백엔드:
- ALLOWED_ORIGINS 기준으로 CORS 허용

프론트:
- VITE_API_BASE_URL 기준으로 API 호출

절대:
- 직접 URL 작성 금지
```

---

## 0.5 Vite 서버 규칙

```text
dev 환경:
- https 사용 가능
- 인증서 사용 가능

build 환경:
- vite dev server 사용하지 않음
- 인증서 설정 영향 없어야 함
```

---

## 0.6 인증서 규칙

```text
로컬:
- SSL_KEY_PATH / SSL_CERT_PATH 사용

배포:
- 인증서 파일 없음 (서버/플랫폼에서 처리)
```

---

## 0.7 FCM / Service Worker 규칙

```text
- 경로: /firebase-messaging-sw.js
- 반드시 production에서도 동작해야 함
```

❌ 금지:

```text
- 상대경로 깨지는 구조
- dev 전용 경로
```

---

## 0.8 배포 동작 방식 (중요)

```text
GitHub main push ≠ 자동 배포 보장
```

가능한 방식:

```text
1. 수동 git pull
2. GitHub Actions
3. 배포 스크립트
```

---

## 0.9 코드 작성 필수 조건

모든 코드는 반드시:

```text
✔ 로컬 dev 정상 동작
✔ npm run build 성공
✔ AWS 배포 환경 정상 동작
```

---

## Merge Conflict 해결 원칙

- Accept Current / Accept Incoming / Accept Both를 기계적으로 선택하지 않는다.
- HEAD 기능과 incoming 기능을 비교해서 둘 다 필요한 경우 제3의 병합 코드를 작성한다.
- HEAD는 현재 작업 브랜치, incoming은 병합해오는 브랜치다.
- 한쪽 전체 파일 선택 금지.
- 중복 import, 중복 함수, 중복 useEffect, 중복 route mount 제거.
- 환경변수 기반 수정은 유지한다.
- main의 기존 서비스 기능은 삭제하지 않는다.
- FCM/PWA/service worker/vite.config 충돌은 반드시 양쪽 의도를 비교한다.
- 충돌 해결 후 `git grep -n "<<<<<<<"`로 마커 잔여 확인.
- 충돌 해결 후 최소 `npm run build` 또는 해당 서버 실행 검증.

## 환경변수 파일 보호 규칙

- `.env`, `.env.*`, `frontend/.env`, `backend/.env` 실파일은 절대 삭제/초기화/덮어쓰기 금지.
- 환경변수 기반으로 코드를 수정할 때도 기존 `.env` 파일의 존재와 값을 보존해야 한다.
- `.env` 파일이 없거나 비어 있으면 임의 생성/초기화하지 말고 사용자에게 보고한다.
- 실제 비밀값, API 키, 도메인 값은 임의로 작성하지 않는다.
- 예시가 필요하면 `.env.example` 또는 문서에만 작성한다.
- 작업 후 `.env` 파일 존재 여부와 크기 변경 여부를 반드시 보고한다.

## 병합 기준

- main 브랜치를 기준으로 병합한다.
- bang 브랜치의 코드를 그대로 덮어쓰지 않는다.
- bang 브랜치에서 더 안정적이거나 추가된 기능만 선별 반영한다.
- UI/UX, 라우트명, 응답 key, DB 스키마, 인증 로직은 변경하지 않는다.
- 환경 전환은 코드 수정이 아니라 `.env` 설정으로 처리하는 것을 목표로 한다.

## 병합 목적

AWS 배포 서버는 GitHub main 브랜치와 연동되어 있으므로, main 브랜치는 항상 배포 가능한 안정 상태를 유지해야 한다.

이번 수동 병합의 목표는 다음과 같다.

1. main 기준 안정성 유지
2. bang 브랜치의 개선 기능 선별 반영
3. 배포 환경과 개발 환경의 설정 분리
4. `.env`, OAuth redirect URI, FCM 토큰 등록 경로, API base URL, HTTPS 설정을 환경별로 정리
5. 병합 후 main에서 배포가 깨지지 않도록 검증


## DB 기준 문서 연동 규칙

DB 스키마의 상세 기준은 `carefull_ohs_db.md`를 함께 읽고 따른다.

AI 작업자는 코드 수정 전 반드시 아래 두 문서를 먼저 확인한다.

```text
1. carefull_ohs.md
2. carefull_ohs_db.md
```

`carefull_ohs.md`는 시스템/환경/병합/로직 기준이고, `carefull_ohs_db.md`는 실제 DB 테이블·컬럼·네이밍 기준이다.

DB 관련 작업 원칙:

```text
- DB 스키마 수정 금지
- 새 마이그레이션 파일 생성 금지
- 새 테이블/새 컬럼 임의 추가 금지
- 존재하지 않는 컬럼 추측 금지
- SQL은 carefull_ohs_db.md에 존재하는 테이블/컬럼 기준으로만 작성
- DB 컬럼명 / SQL alias / API 요청 key / API 응답 key는 snake_case 기준 유지
```

지문 관련 현재 기준:

```text
- patients.fingerprint_slots는 현재 신규 다중 지문 슬롯 기준 컬럼이다.
- patients.fingerprint_id는 DDL에 남아 있는 레거시 단일 지문 ID 컬럼이다.
- 신규 R307 다중 슬롯 등록/삭제 로직을 작성할 때 fingerprint_id 단일값 전제로 되돌리지 않는다.
- fingerprint_id는 DB에서 실제 제거되기 전까지 존재하지 않는 컬럼처럼 취급하지 않는다.
- fingerprints 테이블도 존재하므로 /api/device/fingerprints 병합·수정 시 실제 사용처를 확인한다.
- 지문 저장 방식을 임의로 하나로 통합하거나 DB 스키마를 변경하지 않는다.
```

`device.js` 병합 시 특히 확인할 것:

```text
- /api/device/fingerprint 는 patients.fingerprint_id 기반 레거시 단일 지문 저장 라우트일 수 있으므로 임의 삭제 금지
- /api/device/fingerprints 는 다중 지문 슬롯 라우트이므로 patients.fingerprint_slots 방식인지 fingerprints 테이블 방식인지 사용처 확인 후 병합
- 응답 key 변경 금지
- 라즈베리파이/R307 연동 코드가 기대하는 slot_id, label, registered_at 구조 유지
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

---

## 1. 프로젝트 목적

AI 기반 복약 관리 시스템

목표:

* 복약 스케줄 생성
* 복약 실행 기록
* 미복약 감지
* 보호자 알림
* 대시보드 모니터링

---

## 2. 전체 시스템 흐름 (절대 기준)

[1] 사용자 로그인 → members
[2] 환자 등록 → patients
[3] 기기 등록 → devices
[4] 약 등록 → medications
[5] 스케줄 생성 → schedules
[6] 복약 실행 → activities
[7] 대시보드 조회 → dashboard
[8] 알림 발생 → notifications

---

## 3. 복약 상태 결정 로직 (절대 수정 금지)

```text
SUCCESS:
- face_verified = true
- dispensed = true
- action_verified = true

ERROR:
- error_code 존재 시 무조건 ERROR

FAILED:
- 하나라도 실패 시

MISSED:
- batch job에서 생성
```

---

## 4. 약 잔량 계산 및 알림 로직

```text
remaining_count =
  schedules 총 횟수
  - SUCCESS 활동 수

LOW_STOCK:
- remaining_count ≤ 3
```

---

## 5. DB 설계 기준

상세 테이블/컬럼 기준은 `carefull_ohs_db.md`를 따른다.

```text
- schedules: 하루 n회 = row n개
- activities: 로그 저장
- MISSED: batch 생성
- remaining_count: 저장 금지
- device 상태: last_ping 기준
- patients.fingerprint_slots: 현재 신규 다중 지문 슬롯 기준 컬럼
- patients.fingerprint_id: 레거시 단일 지문 ID 컬럼
- fingerprints: R307 지문 슬롯 테이블
```

주의:

```text
- fingerprint_id 단일값 방식으로 신규 다중 지문 로직을 되돌리지 않는다.
- fingerprint_slots와 fingerprints 테이블 중 어떤 저장소를 쓰는지는 실제 사용처를 확인한 뒤 결정한다.
- 둘 중 하나를 임의 삭제하거나 통합하지 않는다.
```

---

## 6. 대시보드 데이터 가공 원칙

```text
- 단순 조회 금지
- 반드시 계산 포함
```

---

## 7. 시간 처리 규칙

```text
- KST 기준 (Asia/Seoul)

백엔드:
- AT TIME ZONE 필수

프론트:
- toISOString 금지
```

---

## 8. FCM 및 알림 정책

```text
- push_tokens 저장
- 로그인 시 갱신
- activities 생성 시 알림 트리거 실행
```

---

## 9. 관리자 시스템 규칙

```text
/api/admin/*
→ adminAuth 필수
```

---

## 10. API 흐름 기준

(생략 없이 기존 유지)

---

## 11. 프론트-백엔드 연결 원칙

```text
- mock 사용 금지
- API 기준 렌더링
```

---

## 12. AI 코드 생성 제약 조건

```text
- UI 변경 금지
- DB 변경 금지
- 기존 로직 삭제 금지
- JWT 수정 금지
- 구조 변경 금지
- 외부 라이브러리 금지
```

---

## 13. 코드 출력 규칙

```text
- 전체 코드 출력 금지
- diff만 출력
```

---

## 14. 금지 사항

```text
- 계산 로직 변경 금지
- 시간 로직 변경 금지
- 알림 로직 변경 금지
```

---

## 15. 작업 방식

```text
- 원인 분석 → 수정
- 환경(.env) 먼저 확인
```

---

## 최종 기준

```text
이 문서는 절대 기준이다.

특히:
환경 규칙 위반 시
→ 로컬 정상 / 배포 실패 발생
```

반드시 **로컬 + 배포 환경 모두 만족**하도록 구현해야 한다.
