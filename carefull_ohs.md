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

```text
- schedules: 하루 n회 = row n개
- activities: 로그 저장
- MISSED: batch 생성
- remaining_count: 저장 금지
- device 상태: last_ping 기준
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
