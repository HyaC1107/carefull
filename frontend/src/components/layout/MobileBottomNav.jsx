import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import '../../styles/MobileBottomNav.css'

// 이 컴포넌트는 "모바일 전용 하단 탭바"입니다.
// 데스크톱에서는 보이지 않고, 화면이 작을 때만 CSS로 보이게 합니다.
//
// 구조:
// - 자주 쓰는 메뉴 4개: 대시보드 / 복약 일정 / 알림 / 환자 정보
// - 더보기 버튼 1개: 통계 / 설정
//
// 현재는 대시보드(/dashboard), 복약 일정(/schedule) 페이지 이동이 연결되어 있습니다.
// 알림 / 환자 정보 / 통계 / 설정은 아직 준비 중이며,
// 나중에 해당 페이지 라우트가 생기면 navigate()를 추가로 연결하면 됩니다.
function MobileBottomNav({ activeMenu = 'dashboard' }) {
  const navigate = useNavigate()
  const [isMoreOpen, setIsMoreOpen] = useState(false)

  // 하단 탭바에 바로 노출할 메뉴
  const primaryItems = [
    { key: 'dashboard', label: '대시보드' },
    { key: 'schedule', label: '일정' },
    { key: 'alerts', label: '알림' },
    { key: 'patient', label: '환자' },
  ]

  // 더보기 버튼이 활성 상태로 보여야 하는 조건
  // 1) 더보기 패널이 열려 있거나
  // 2) 현재 페이지가 stats 또는 settings일 때
  const isMoreActive =
    isMoreOpen || activeMenu === 'stats' || activeMenu === 'settings'

  // 더보기 안에 넣을 메뉴
  const extraItems = [
    { key: 'stats', label: '통계' },
    { key: 'settings', label: '설정' },
  ]

    // 메뉴 클릭 처리
    // 현재는 dashboard, schedule 페이지는 실제 이동.
    // 나머지 메뉴는 아직 준비 중이라 콘솔 로그만 출력.
    // 나중에 페이지가 생기면 switch 안에 navigate('/alerts') 같은 식으로 추가하면 됨.
    const handleMenuClick = (menuKey) => {
      switch (menuKey) {
        case 'dashboard':
          navigate('/dashboard')
          setIsMoreOpen(false)
          break

        case 'schedule':
          navigate('/schedule')
          setIsMoreOpen(false)
          break

        case 'alerts':
          navigate('/alerts')
          setIsMoreOpen(false)
          break

        case 'stats':
          navigate('/stats')
          setIsMoreOpen(false)
          break

        case 'patient':
          navigate('/patient')
          setIsMoreOpen(false)
          break
          
        case 'settings':
          navigate('/settings')
          setIsMoreOpen(false)
          break
          
        default:
          break
      }
    }

  return (
    <>
      {/* 더보기 패널이 열렸을 때 어두운 배경 */}
      {isMoreOpen ? (
        <button
          type="button"
          className="mobile-bottom-nav__backdrop"
          onClick={() => setIsMoreOpen(false)}
          aria-label="더보기 닫기"
        />
      ) : null}

      {/* 더보기 패널 */}
      {isMoreOpen ? (
        <div className="mobile-bottom-nav__sheet">
          <p className="mobile-bottom-nav__sheet-title">더보기</p>

          <div className="mobile-bottom-nav__sheet-list">
            {extraItems.map((item) => (
              <button
                key={item.key}
                type="button"
                className="mobile-bottom-nav__sheet-button"
                onClick={() => handleMenuClick(item.key)}
              >
                <span className="mobile-bottom-nav__sheet-icon" aria-hidden="true">
                  {renderMenuIcon(item.key)}
                </span>
                <span>{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {/* 모바일 하단 탭바 */}
      <nav className="mobile-bottom-nav" aria-label="모바일 하단 메뉴">
        {primaryItems.map((item) => {
          const isActive = item.key === activeMenu

          return (
            <button
              key={item.key}
              type="button"
              className={`mobile-bottom-nav__button ${
                isActive ? 'mobile-bottom-nav__button--active' : ''
              }`}
              onClick={() => handleMenuClick(item.key)}
            >
              <span className="mobile-bottom-nav__icon" aria-hidden="true">
                {renderMenuIcon(item.key)}
              </span>
              <span className="mobile-bottom-nav__label">{item.label}</span>
            </button>
          )
        })}

        {/* 더보기 버튼 */}
        <button
          type="button"
          className={`mobile-bottom-nav__button ${
            isMoreActive ? 'mobile-bottom-nav__button--active' : ''
          }`}
          onClick={() => setIsMoreOpen((prev) => !prev)}
        >
          <span className="mobile-bottom-nav__icon" aria-hidden="true">
            {renderMenuIcon('more')}
          </span>
          <span className="mobile-bottom-nav__label">더보기</span>
        </button>
      </nav>
    </>
  )
}

// 하단 탭바 아이콘 SVG
function renderMenuIcon(menuKey) {
  switch (menuKey) {
    case 'dashboard':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 10.5 12 3l9 7.5" />
          <path d="M5 9.5V20h14V9.5" />
        </svg>
      )

    case 'schedule':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="5" width="16" height="15" rx="2" />
          <path d="M8 3v4M16 3v4M4 9h16" />
        </svg>
      )

    case 'alerts':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9" />
          <path d="M10 21a2 2 0 0 0 4 0" />
        </svg>
      )

    case 'patient':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
        </svg>
      )

    case 'stats':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 20V10" />
          <path d="M10 20V4" />
          <path d="M16 20v-7" />
          <path d="M22 20V8" />
        </svg>
      )

    case 'settings':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h0a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z" />
        </svg>
      )

    case 'more':
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
          <circle cx="5" cy="12" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="19" cy="12" r="2" />
        </svg>
      )

    default:
      return null
  }
}

export default MobileBottomNav