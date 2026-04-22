# Frontend 코드 검토 보고서

> 작성일: 2026-04-22  
> 대상: carefull/frontend (React.js 보호자 대시보드)

---

## 1. 기술 스택

| 항목 | 내용 |
|---|---|
| 빌드 도구 | Vite 8.0.4 |
| UI 라이브러리 | React 19.2.4 |
| 라우팅 | React Router v7 |
| 차트 | Recharts 3.8.1 |
| 아이콘 | react-icons 5.6.0 |
| 스타일 | 순수 CSS (페이지·컴포넌트별 분리) |
| 상태 관리 | React 로컬 State (useState/useMemo) |

---

## 2. 폴더 구조

```
frontend/
├── src/
│   ├── pages/                  # 페이지 컴포넌트 (7개)
│   │   ├── LoginPage.jsx
│   │   ├── DashboardPage.jsx
│   │   ├── SchedulePage.jsx
│   │   ├── StatsPage.jsx
│   │   ├── AlertsPage.jsx
│   │   ├── PatientPage.jsx
│   │   └── SettingsPage.jsx
│   ├── components/             # 재사용 컴포넌트
│   │   ├── layout/             # Sidebar, TopHeader, MobileBottomNav
│   │   ├── auth/               # LoginCard, SocialLoginButton
│   │   ├── dashboard/
│   │   ├── alerts/
│   │   ├── schedule/
│   │   ├── stats/
│   │   ├── patient/
│   │   └── settings/
│   ├── data/                   # Mock 데이터 (페이지별)
│   ├── styles/                 # CSS (페이지·컴포넌트별)
│   ├── App.jsx                 # 라우팅 설정
│   └── main.jsx                # 진입점
├── package.json
├── vite.config.js
└── index.html
```

---

## 3. 라우팅 구조

| 경로 | 페이지 | 설명 |
|---|---|---|
| `/` | → `/login` | 기본 리디렉션 |
| `/login` | LoginPage | 소셜 로그인 |
| `/dashboard` | DashboardPage | 복약 현황 요약 |
| `/schedule` | SchedulePage | 복약 일정 달력 |
| `/stats` | StatsPage | 복약 통계 차트 |
| `/alerts` | AlertsPage | 알림 이력 |
| `/patient` | PatientPage | 환자 정보 관리 |
| `/settings` | SettingsPage | 알림·기기·계정 설정 |
| `/*` | → `/login` | 미정의 경로 처리 |

---

## 4. 페이지별 기능 요약

### 4.1 LoginPage
- 카카오 / 네이버 / 구글 소셜 로그인 버튼 UI
- **현재:** 버튼 클릭 시 `/dashboard`로 직접 이동 (OAuth 미구현)

### 4.2 DashboardPage
- SummaryCard 4개 (성공률, 예정, 완료, 미복용)
- DeviceStatusSection (기기 연결 상태, 남은 복용 횟수)
- AlertsSection (최근 알림 4개)
- NextMedicationBanner (다음 복약 알림)
- 데스크톱: Sidebar / 모바일: MobileBottomNav

### 4.3 SchedulePage
- 월간 달력 UI, 날짜별 복약 일정 표시
- 복약 상태 토글 (pending ↔ done)
- 일정 추가 모달
- `useMemo`로 선택 날짜 일정 필터링 최적화

### 4.4 StatsPage
- BarChartCard: 월별 복약 성공률 (막대 그래프)
- LineChartCard: 시간대별 복약 패턴 (선 그래프)
- PieChartCard: 약물별 복약률 (도넛 차트)
- StatsSummaryGrid: 4개 요약 지표
- WeeklyInsightSection: 주간 인사이트 텍스트

### 4.5 AlertsPage
- 타입별 필터 탭 (전체 / 완료 / 주의 / 미복용)
- 읽음·안 읽음 상태 관리
- "모두 읽음 처리" 버튼
- `useMemo`로 필터링 최적화

### 4.6 PatientPage
- 미등록 상태: PatientEmptyState (등록 유도)
- 등록 완료 상태: 프로필 + 약물 + 기기 정보 표시
- PatientRegisterModal: 이름·연락처·사진 촬영 필수
- DeviceRegisterModal: 시리얼 번호·기기명 필수

### 4.7 SettingsPage
- 알림 설정: SMS 토글, 알림 시간
- 디바이스 설정: 자동 동기화, 알림 소리, 음성 안내
- 계정 설정: 보호자 정보 수정 모달
- GuardianEditModal: 이름·연락처·주소·이메일·관계 수정

---

## 5. 상태 관리 패턴

전역 상태 관리 라이브러리 없이 **페이지별 로컬 State**로만 관리.

| 페이지 | 주요 상태 |
|---|---|
| SchedulePage | calendarState, scheduleMap, isAddModalOpen |
| AlertsPage | activeFilter, alerts |
| PatientPage | patientData, deviceData, isPatientModalOpen, isDeviceModalOpen |
| SettingsPage | settings, guardianInfo, isGuardianModalOpen |

---

## 6. 스타일링

- 순수 CSS, 페이지·컴포넌트별 파일 분리
- BEM 네이밍 규칙 (`summary-card__title`, `summary-card__icon--success`)
- 반응형: 모바일 MobileBottomNav / 데스크톱 Sidebar CSS 분리
- 전역 폰트: Pretendard, Noto Sans KR, Apple SD Gothic Neo

**주요 컬러 시스템:**

| 상태 | 색상 |
|---|---|
| 성공 | green (#16a34a, #10b981) |
| 실패 | red (#ef4444) |
| 경고 | amber (#f59e0b) |
| 정보 | blue (#2563eb, #3b82f6) |

---

## 7. 현재 데이터 흐름

```
src/data/*.js (Mock)
       ↓
   pages/*.jsx (import)
       ↓
  components (props)
```

실제 API 연동 없이 모든 데이터가 하드코딩된 Mock 데이터로 동작 중.

---

## 8. 문제점 및 개선 사항

### 8.1 우선순위 높음 (HIGH)

| 문제 | 내용 | 권장 해결책 |
|---|---|---|
| API 연동 부재 | 모든 데이터가 Mock | axios 또는 fetch로 REST API 연동 |
| 인증 미구현 | 누구나 모든 페이지 접근 가능 | OAuth 연동, JWT 토큰 저장 (httpOnly cookie 권장) |
| 전역 상태 없음 | 로그인 정보 공유 불가 | Context API 또는 Zustand 도입 |
| 에러 처리 없음 | try-catch, Error Boundary 없음 | 에러 경계 추가, 네트워크 오류 대응 |
| 로딩 상태 없음 | API 호출 중 UI 피드백 없음 | 스켈레톤 UI 또는 스피너 추가 |

### 8.2 우선순위 중간 (MEDIUM)

| 문제 | 내용 | 권장 해결책 |
|---|---|---|
| 폼 검증 부족 | 실시간 검증, 상세 오류 메시지 없음 | react-hook-form + Zod 도입 |
| 하드코딩 | TopHeader에 "이영희", "김보호" 등 고정값 | 전역 상태에서 동적으로 주입 |
| 로그아웃 없음 | 세션 종료 수단 없음 | 설정 페이지에 로그아웃 추가 |
| 보안 취약 | XSS 가능성, 민감 정보 Mock 포함 | 입력 sanitize, 실제 데이터 정리 |

### 8.3 우선순위 낮음 (LOW)

| 문제 | 내용 | 권장 해결책 |
|---|---|---|
| 테스트 코드 없음 | 단위·E2E 테스트 전무 | Jest + React Testing Library |
| TypeScript 미적용 | 타입 안전성 없음 | 점진적 TypeScript 마이그레이션 |
| 접근성(A11y) 부족 | aria-label 등 대체 텍스트 부족 | 접근성 감사 후 보완 |
| 번들 최적화 없음 | Code splitting 없음 | React.lazy + Suspense 적용 |

---

## 9. 개선 로드맵 (권장 순서)

```
1단계 (즉시)
  ├── 백엔드 API 연동 (axios 인스턴스 설정)
  ├── 소셜 OAuth 로그인 구현
  └── Protected Route (인증 없으면 /login 리디렉션)

2단계 (단기)
  ├── Context API로 인증 상태 전역 관리
  ├── 에러 처리 (Error Boundary + toast 알림)
  └── 로딩 스켈레톤 UI

3단계 (중기)
  ├── react-hook-form + Zod 폼 검증
  ├── 단위 테스트 작성
  └── 접근성 개선

4단계 (장기)
  ├── TypeScript 마이그레이션
  └── 성능 최적화 (Code splitting, 이미지 최적화)
```

---

## 10. 강점 요약

- 페이지·컴포넌트 역할 분리가 명확함
- BEM 기반 CSS 네이밍이 일관됨
- 모바일·데스크톱 반응형 레이아웃 구현됨
- Recharts를 활용한 통계 시각화 구성 완료
- `useMemo`로 불필요한 재계산 일부 최적화

---

*이 문서는 프로토타입 단계 코드를 기준으로 작성되었습니다. 백엔드 API 연동 이후 재검토 권장.*
