import { useNavigate } from 'react-router-dom'
import '../../styles/Sidebar.css'

// 이 컴포넌트는 왼쪽 사이드바 전체를 담당합니다.
// 현재는 대시보드(/dashboard), 복약 일정(/schedule) 페이지 이동이 연결되어 있습니다.
// 통계 / 알림 / 환자 정보 / 설정 페이지는 아직 준비 중이며,
// 나중에 React Router 경로가 만들어지면 navigate()를 추가로 연결하면 됩니다.
function Sidebar({ activeMenu = 'dashboard', alertCount = 0 }) {
  const navigate = useNavigate()

  const menuItems = [
    { key: 'dashboard', label: '대시보드' },
    { key: 'schedule', label: '복약 일정' },
    { key: 'stats', label: '통계' },
    { key: 'alerts', label: '알림', badgeCount: alertCount },
    { key: 'patient', label: '환자 정보' },
    { key: 'settings', label: '설정' },
  ]

  const handleMenuClick = (menuKey) => {
    switch (menuKey) {
      case 'dashboard':
        navigate('/dashboard')
        break
      case 'schedule':
        navigate('/schedule')
        break
      case 'stats':
        navigate('/stats')
        break
      case 'alerts':
        navigate('/alerts')
        break
      case 'patient':
        navigate('/patient')
        break
      case 'settings':
        navigate('/settings')
        break 
    default:
        break
    }
  }

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="18"
            height="18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10 13a4 4 0 0 1 0-6l1.2-1.2a4 4 0 0 1 5.6 5.6L15.5 12" />
            <path d="M14 11a4 4 0 0 1 0 6l-1.2 1.2a4 4 0 0 1-5.6-5.6L8.5 12" />
          </svg>
        </div>

        <div>
          <h2 className="sidebar__title">스마트 복약</h2>
          <p className="sidebar__subtitle">Smart Medication</p>
        </div>
      </div>

      <nav className="sidebar__nav">
        {menuItems.map((item) => {
          const isActive = item.key === activeMenu

          return (
            <button
              key={item.key}
              type="button"
              className={`sidebar__menu-button ${isActive ? 'sidebar__menu-button--active' : ''}`}
              onClick={() => handleMenuClick(item.key)}
            >
            <span className="sidebar__menu-icon" aria-hidden="true">
              {renderMenuIcon(item.key)}
              </span>

              <span className="sidebar__menu-text">{item.label}</span>

              {item.badgeCount > 0 ? (
                <span className="sidebar__menu-badge">{item.badgeCount}</span>
              ) : null}
            </button>
          )
        })}
      </nav>

    </aside>
  )
}

function renderMenuIcon(menuKey) {
  switch (menuKey) {
    case 'dashboard':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 10.5 12 3l9 7.5" />
          <path d="M5 9.5V20h14V9.5" />
        </svg>
      )
    case 'schedule':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4" y="5" width="16" height="15" rx="2" />
          <path d="M8 3v4M16 3v4M4 9h16" />
        </svg>
      )
    case 'stats':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M4 20V10" />
          <path d="M10 20V4" />
          <path d="M16 20v-7" />
          <path d="M22 20V8" />
        </svg>
      )
    case 'alerts':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9" />
          <path d="M10 21a2 2 0 0 0 4 0" />
        </svg>
      )
    case 'patient':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
        </svg>
      )
    case 'settings':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h0a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 1 1.5h0a1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v0a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z" />
        </svg>
      )
    default:
      return null
  }
}

export default Sidebar
