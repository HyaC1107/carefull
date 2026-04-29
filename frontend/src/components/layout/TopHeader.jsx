import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHeaderData } from '../../context/HeaderDataContext'
import '../../styles/TopHeader.css'

function TopHeader() {
  const navigate = useNavigate()
  const data = useHeaderData()
  const [failedImg, setFailedImg] = useState('')

  const patientLabel = data?.patientLabel ?? '환자: -'
  const guardianName = data?.guardianName ?? '-'
  const profileImg = data?.profileImg ?? ''
  const deviceStatusText = data?.deviceStatusText ?? '기기 상태 확인 중'
  const lastSyncedText = data?.lastSyncedText ?? '-'

  const isUnregistered = patientLabel.includes('등록해주세요')
  const showImg = profileImg && failedImg !== profileImg

  return (
    <header className="top-header">
      <div className="top-header__title-group">
        <h1 className="top-header__title">복약 모니터링 대시보드</h1>
        <p
          className="top-header__subtitle"
          role={isUnregistered ? 'button' : undefined}
          tabIndex={isUnregistered ? 0 : undefined}
          onClick={isUnregistered ? () => navigate('/patient') : undefined}
          onKeyDown={isUnregistered ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/patient') } } : undefined}
        >
          {patientLabel}
        </p>
      </div>

      <div className="top-header__right">
        <div className="top-header__device">
          <div className="top-header__device-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 12a10 10 0 0 1 14 0" />
              <path d="M8.5 15.5a5 5 0 0 1 7 0" />
              <path d="M12 19h.01" />
            </svg>
          </div>
          <div>
            <p className="top-header__device-status">{deviceStatusText}</p>
            <p className="top-header__device-time">마지막 동기화: {lastSyncedText}</p>
          </div>
        </div>

        <div className="top-header__divider" />

        <div className="top-header__guardian">
          <div className="top-header__guardian-avatar" aria-hidden="true">
            {showImg ? (
              <img
                className="top-header__guardian-avatar-img"
                src={profileImg}
                alt=""
                onError={() => setFailedImg(profileImg)}
              />
            ) : (
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="8" r="4" />
                <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
              </svg>
            )}
          </div>
          <div>
            <p className="top-header__guardian-role">보호자</p>
            <p className="top-header__guardian-name">{guardianName}</p>
          </div>
        </div>
      </div>
    </header>
  )
}

export default TopHeader
