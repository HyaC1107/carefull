import '../../styles/TopHeader.css'

// 이 컴포넌트는 상단 파란 헤더를 담당합니다.
// 페이지 제목, 환자 정보, 기기 연결 상태, 보호자 정보를 보여줍니다.
function TopHeader() {
  return (
    <header className="top-header">
      {/* 왼쪽: 페이지 제목 영역 */}
      <div className="top-header__title-group">
        <h1 className="top-header__title">복약 모니터링 대시보드</h1>
        <p className="top-header__subtitle">환자: 이영희 (76세)</p>
      </div>

      {/* 오른쪽: 기기 상태 + 보호자 영역 */}
      <div className="top-header__right">
        <div className="top-header__device">
          <div className="top-header__device-icon" aria-hidden="true">
            {/* 기기 연결 상태 아이콘 */}
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12a10 10 0 0 1 14 0" />
              <path d="M8.5 15.5a5 5 0 0 1 7 0" />
              <path d="M12 19h.01" />
            </svg>
          </div>
          <div>
            <p className="top-header__device-status">기기 연결됨</p>
            <p className="top-header__device-time">마지막 동기화: 5분 전</p>
          </div>
        </div>

        <div className="top-header__divider" />

        <div className="top-header__guardian">
          <div className="top-header__guardian-avatar" aria-hidden="true">
            {/* 보호자 아이콘 */}
            <svg
              viewBox="0 0 24 24"
              width="16"
              height="16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
            </svg>
          </div>
          <div>
            <p className="top-header__guardian-role">보호자</p>
            <p className="top-header__guardian-name">김보호</p>
          </div>
        </div>
      </div>
    </header>
  )
}

export default TopHeader