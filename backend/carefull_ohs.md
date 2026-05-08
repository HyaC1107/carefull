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
- 현재 공식 지문 저장 컬럼은 patients.fingerprint_slots 하나다.
- patients.fingerprint_slots 타입은 jsonb이며 기본값은 '[]'::jsonb, NOT NULL이다.
- patients.삭제된 단일 지문 ID 컬럼은 현재 DB 기준에서 삭제되었으므로 조회/INSERT/UPDATE/RETURNING 하지 않는다.
- 별도 지문 테이블 방식으로 전환하지 않는다.
- 지문 슬롯 구조는 { slot_id, label, registered_at } 배열을 유지한다.
- 지문 저장 방식은 patients.fingerprint_slots 기준으로 유지하며 DB 스키마를 변경하지 않는다.
```

`device.js` 병합 시 특히 확인할 것:

```text
- 지문 관련 라우트는 patients.fingerprint_slots jsonb 배열 기준으로 동작해야 한다.
- 단일 지문 ID 컬럼 저장 방식으로 되돌리지 않는다.
- 별도 지문 테이블 방식으로 전환하지 않는다.
- 응답 key 변경 금지
- 라즈베리파이/R307 연동 코드가 기대하는 slot_id, label, registered_at 구조 유지
```


## 지문 컬럼 최종 기준

현재 DB 기준에서 공식 지문 저장 컬럼은 `patients.fingerprint_slots`다.

따라서 AI 작업자는 아래 규칙을 반드시 따른다.

- `patients.fingerprint_slots` 타입은 `jsonb DEFAULT '[]'::jsonb NOT NULL`이다.
- 삭제된 단일 지문 ID 컬럼을 조회/INSERT/UPDATE/RETURNING 하지 않는다.
- 단일 지문 ID 요청 key 또는 응답 key를 신규 코드에 추가하지 않는다.
- 지문 슬롯 기준은 `patients.fingerprint_slots`다.
- 지문 조회/등록/삭제 로직은 `fingerprint_slots jsonb` 기준으로 처리한다.
- `fingerprint_slots` 구조는 `{ slot_id, label, registered_at }` 배열을 유지한다.
- 별도 지문 테이블 방식으로 되돌리지 않는다.
- DB 스키마를 다시 변경하거나 삭제된 단일 지문 ID 컬럼을 재추가하지 않는다.

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
- patients.fingerprint_slots: 현재 공식 다중 지문 슬롯 기준 컬럼, jsonb DEFAULT '[]'::jsonb NOT NULL
- 단일 지문 ID 컬럼: 현재 DB 기준 삭제됨
- 별도 지문 테이블: 사용하지 않음. 지문 공식 저장 기준은 patients.fingerprint_slots
```

주의:

```text
- 단일 지문 ID 방식으로 신규 다중 지문 로직을 되돌리지 않는다.
- 지문 저장소는 patients.fingerprint_slots만 공식으로 사용한다.
- 별도 지문 테이블 방식으로 변경하지 않는다.
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


---

## 8.1 보호자 목소리 / ElevenLabs 음성 알림 흐름

보호자 목소리 기능은 **녹음 파일을 그대로 재생하는 기능이 아니다.**
보호자 음성 샘플로 ElevenLabs voice clone을 생성하고, 고정 안내 문구를 해당 목소리로 TTS 변환한 뒤 디바이스에서 mp3를 재생하는 구조다.

전체 흐름:

```text
[1] 보호자가 1분 정도 목소리 녹음 또는 음성 파일 업로드
[2] 프론트엔드가 POST /api/voice/upload 호출
[3] 백엔드가 multer로 음성 파일을 uploads/voices에 저장
[4] voice_samples 테이블에 status = 'pending' 으로 저장
[5] 서버가 ElevenLabs Voice Cloning API에 음성 샘플 전달
[6] ElevenLabs가 보호자 목소리 voice_id 생성
[7] 서버가 voice_samples.elevenlabs_voice_id에 voice_id 저장
[8] 서버가 "약 먹을 시간이에요" 같은 안내 텍스트를 ElevenLabs TTS API에 전달
[9] ElevenLabs가 보호자 목소리 느낌의 mp3 생성
[10] 서버가 mp3를 uploads/sounds에 저장
[11] 서버가 devices.alarm_sound_path / alarm_sound_name / alarm_sound_updated_at 업데이트
[12] 디바이스가 GET /api/device/sound?device_uid=... 로 알림음 메타 조회
[13] 디바이스가 file_path를 서버 URL과 조합해 mp3 다운로드
[14] 디바이스 스피커로 mp3 출력
```

역할 구분:

```text
Voice Cloning:
- 보호자 음성 샘플을 기반으로 ElevenLabs voice_id 생성
- 결과물은 재생 파일이 아니라 voice_id

Text to Speech:
- voice_id + 안내 문구를 이용해 mp3 생성
- 결과물은 디바이스가 재생할 alarm_voice_*.mp3 파일
```

아래 기능과 혼동하지 않는다:

```text
보이스 아이솔레이터:
- 배경음/잡음/목소리 분리 기능
- 현재 보호자 음성 알림 핵심 기능 아님

보이스 체인저:
- 이미 존재하는 음성을 다른 목소리처럼 변환하는 기능
- 현재 구조의 핵심 아님

음성 텍스트 변환(STT):
- 음성을 글자로 변환하는 기능
- 현재 구조의 핵심 아님
```

---

## 8.2 보호자 목소리 관련 파일 기준

AI/Codex 작업자는 보호자 목소리 또는 알림음 기능 수정 전 아래 파일을 우선 확인한다.

```text
프론트엔드:
- frontend/src/pages/SettingsPage.jsx
- frontend/src/components/settings/VoiceUploadTab.jsx
- frontend/src/components/settings/AlarmSoundTab.jsx
- frontend/src/api.js

백엔드:
- backend/server.js
- backend/routes/voice.js
- backend/routes/device.js
- backend/services/elevenlabs.service.js

DB 문서:
- backend/carefull_ohs_db.md

라즈베리파이/디바이스:
- sound_sync.py
- alarm.py
- 디바이스 설정 또는 환경변수 파일
```

현재 기준으로 확인된 주요 연결점:

```text
프론트 업로드 field 이름:
- voice

백엔드 multer field 이름:
- upload.single('voice')

음성 샘플 저장 경로:
- uploads/voices

TTS mp3 저장 경로:
- uploads/sounds

정적 파일 서빙:
- /uploads

디바이스 알림음 조회 API:
- GET /api/device/sound?device_uid=...

알림음 DB 컬럼:
- devices.alarm_sound_path
- devices.alarm_sound_name
- devices.alarm_sound_updated_at

음성 샘플 DB 테이블:
- voice_samples

음성 상태값:
- pending
- processing
- ready
- error
```

주의:

```text
- voice_samples.status에 processing이 정의되어 있어도 실제 코드에서 사용하지 않을 수 있으므로 코드 기준으로 확인한다.
- 업로드 직후 프론트가 완료 화면을 보여도 ElevenLabs 변환은 아직 pending일 수 있다.
- ready/error 상태 polling이 없으면 사용자가 실제 변환 성공 여부를 즉시 알 수 없다.
- devices 업데이트는 연결된 device row가 있어야 반영된다.
- devices UPDATE rowCount가 0일 수 있으므로 디버깅 시 반드시 확인한다.
```

---

## 8.3 ElevenLabs 연동 기준

ElevenLabs 연동은 서버에서만 수행한다.
프론트엔드 또는 디바이스에 ElevenLabs API Key를 노출하지 않는다.

필수 환경변수:

```env
ELEVENLABS_API_KEY=
VOICE_CALLBACK_SECRET=
```

규칙:

```text
- ELEVENLABS_API_KEY는 backend/.env에만 둔다.
- 실제 API Key 값은 문서, 로그, 프론트 코드, 라즈베리파이 코드에 출력하지 않는다.
- .env 실파일은 삭제/초기화/덮어쓰기 금지다.
- 예시는 .env.example 또는 문서에만 작성한다.
```

ElevenLabs API 사용 기준:

```text
Voice Clone:
- 보호자 음성 샘플을 multipart/form-data로 전달
- 결과 voice_id를 voice_samples.elevenlabs_voice_id에 저장

Text to Speech:
- voice_id와 안내 문구를 전달
- mp3 결과를 uploads/sounds에 저장
- 저장 후 devices.alarm_sound_* 컬럼을 갱신
```

확인해야 할 위험 지점:

```text
- /voices/add 요청의 FormData 필드명이 공식 명세와 맞는지 확인
- /text-to-speech/{voice_id} 요청의 model_id가 한국어 TTS에 적합한지 확인
- output_format이 디바이스 재생 가능한 mp3 형식인지 확인
- Node.js 배포 버전이 FormData / Blob 전역 객체를 지원하는지 확인
- ElevenLabs 실패 응답을 로그로 확인할 수 있는지 확인
- API 실패 시 voice_samples.status = 'error' 흐름이 보장되는지 확인
```

외부 라이브러리 추가 금지 원칙은 유지한다.
단, Node 런타임 호환성 문제는 먼저 Node 버전 확인으로 판단한다.

---

## 8.4 디바이스 알림음 동기화 기준

디바이스는 ElevenLabs API를 직접 호출하지 않는다.
디바이스는 서버가 생성한 mp3 파일만 조회/다운로드/재생한다.

디바이스 기준 흐름:

```text
[1] 디바이스가 device_uid를 기준으로 서버에 알림음 메타 조회
[2] GET /api/device/sound?device_uid=... 호출
[3] 응답의 sound.file_path, sound.file_name, sound.updated_at 확인
[4] 기존 local updated_at과 비교
[5] 변경된 경우에만 mp3 다운로드
[6] 로컬에 저장된 mp3를 alarm.py에서 재생
```

주의:

```text
- /api/device/sound 응답이 file_path만 주면 디바이스가 API_ORIGIN과 조합해야 한다.
- file_path가 uploads/sounds/... 형태면 실제 접근은 /uploads/sounds/... 형태가 되어야 한다.
- API_ORIGIN, SERVER_URL, device_uid는 하드코딩하지 않고 환경변수 또는 설정 파일 기준으로 관리한다.
- device_uid만으로 조회 가능한 구조는 기기용 설계일 수 있으나, 노출 시 알림음 메타 조회 위험이 있으므로 임의로 확장하지 않는다.
```

라즈베리파이 관련 코드에서 확인할 것:

```text
- sound_sync.py가 updated_at 기준으로 새 파일만 다운로드하는지
- download_sound()가 file_path URL을 올바르게 조합하는지
- alarm.py가 로컬 mp3 경로를 사용해 재생하는지
- mpg123 등 시스템 의존성이 필요한지
- poll_seconds와 프론트 안내 문구가 일치하는지
```

---

## 8.5 보호자 목소리 기능 작업 금지/주의 사항

금지:

```text
- ElevenLabs API Key를 프론트엔드에 노출 금지
- ElevenLabs API Key를 라즈베리파이에 배포 금지
- 녹음 파일을 그대로 최종 알림음으로 간주 금지
- voice_id를 mp3 파일 경로로 오해 금지
- 보이스 아이솔레이터/보이스 체인저/STT 기능으로 잘못 구현 금지
- devices.alarm_sound_* 응답 key 변경 금지
- /api/voice, /api/device/sound 라우트명 변경 금지
- voice_samples / devices DB 스키마 변경 금지
- 새 테이블/새 컬럼/새 마이그레이션 임의 생성 금지
- 외부 라이브러리 임의 추가 금지
- URL/도메인/포트 하드코딩 금지
```

수정 전 확인:

```text
1. carefull_ohs.md 확인
2. carefull_ohs_db.md 확인
3. frontend VoiceUploadTab 업로드 field 확인
4. backend voice 라우트의 multer field 확인
5. elevenlabs.service.js의 API 요청 방식 확인
6. device.js의 /api/device/sound 응답 구조 확인
7. server.js의 /uploads 정적 서빙 확인
8. raspberry sound_sync.py / alarm.py 확인
```

Codex 출력 기준:

```text
- 전체 코드 출력 금지
- 수정 파일 목록 출력
- 핵심 diff만 출력
- 변경 이유를 파일별로 짧게 설명
- 기존 UI/UX 변경 금지
- 기존 라우트명/응답 key 변경 금지
- 기존 인증/JWT 구조 변경 금지
- 기존 DB 스키마 변경 금지
```

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

---

## 지문 저장 기준 최종 확정

현재 프로젝트의 공식 지문 저장 기준은 `patients.fingerprint_slots`이다.

- 지문 데이터는 별도 지문 테이블에 저장하지 않는다.
- `fingerprint_slots`는 여러 지문 슬롯을 담는 JSONB 배열이며 타입은 `jsonb DEFAULT '[]'::jsonb NOT NULL`이다.
- 지문 조회/등록/삭제 로직은 `patients.fingerprint_slots` 기준으로 동작한다.
- `fingerprint_slots` 항목 구조는 `{ slot_id, label, registered_at }`를 유지한다.
- 별도 지문 테이블 기반 `SELECT` / `INSERT` / `DELETE` / `UPDATE` 전환은 사용하지 않는다.
- `fp_id` 응답 key 전환은 사용하지 않는다.
- 향후 AI/Codex 작업 시 지문 흐름을 별도 테이블 방식으로 변경하지 않는다.
- DB 스키마 변경 없이 기존 `fingerprint_slots` 구조를 유지한다.
- 이 문단은 문서 내 과거 지문 테이블 언급보다 우선하는 최종 기준이다.
