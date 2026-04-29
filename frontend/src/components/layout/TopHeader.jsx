import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getDeviceStatus,
  getDeviceStatusClass,
  getDeviceStatusText,
  getStoredToken,
  hasStoredToken,
  requestJson,
} from '../../api'
import '../../styles/TopHeader.css'

let cachedHeaderToken = ''
let cachedHeaderData = null
let cachedHeaderPromise = null
const TOP_HEADER_REFRESH_EVENT = 'carefull:top-header-refresh'
const PATIENT_REGISTRATION_LABEL = '환자를 등록해주세요.'

function TopHeader({
  patientLabel,
  guardianName,
  deviceStatusText,
  deviceStatusClass,
  lastSyncedText,
  profileImg,
}) {
  const navigate = useNavigate()
  const [sharedHeaderData, setSharedHeaderData] = useState(() =>
    shouldReuseCachedHeader() ? cachedHeaderData : null,
  )
  const [failedProfileImg, setFailedProfileImg] = useState('')

  useEffect(() => {
    const needsSharedHeader =
      patientLabel === undefined ||
      guardianName === undefined ||
      deviceStatusText === undefined ||
      deviceStatusClass === undefined ||
      lastSyncedText === undefined ||
      profileImg === undefined

    if (!needsSharedHeader || !hasStoredToken()) {
      return
    }

    let isMounted = true

    loadSharedHeaderData()
      .then((data) => {
        if (isMounted) {
          setSharedHeaderData(data)
        }
      })
      .catch((error) => {
        console.error('top header fetch error:', error)
      })

    return () => {
      isMounted = false
    }
  }, [
    deviceStatusClass,
    deviceStatusText,
    guardianName,
    lastSyncedText,
    patientLabel,
    profileImg,
  ])

  const resolvedProfileImg = profileImg ?? sharedHeaderData?.profileImg ?? ''
  const shouldShowProfileImg =
    resolvedProfileImg && failedProfileImg !== resolvedProfileImg

  useEffect(() => {
    const handleHeaderRefresh = () => {
      clearTopHeaderCache()

      if (!hasStoredToken()) {
        return
      }

      loadSharedHeaderData()
        .then((data) => {
          setSharedHeaderData(data)
        })
        .catch((error) => {
          console.error('top header refresh error:', error)
        })
    }

    window.addEventListener(TOP_HEADER_REFRESH_EVENT, handleHeaderRefresh)

    return () => {
      window.removeEventListener(TOP_HEADER_REFRESH_EVENT, handleHeaderRefresh)
    }
  }, [])

  const resolvedPatientLabel =
    patientLabel ?? sharedHeaderData?.patientLabel ?? '환자: -'
  const shouldNavigateToPatientRegistration = resolvedPatientLabel.includes(
    PATIENT_REGISTRATION_LABEL,
  )
  const resolvedGuardianName =
    resolveDisplayName(guardianName) ||
    resolveDisplayName(sharedHeaderData?.guardianName) ||
    '-'
  const resolvedDeviceStatusText =
    deviceStatusText ?? sharedHeaderData?.deviceStatusText ?? '미연결'
  const resolvedDeviceStatusClass =
    deviceStatusClass ?? sharedHeaderData?.deviceStatusClass ?? 'status-disconnected'
  const resolvedLastSyncedText =
    lastSyncedText ?? sharedHeaderData?.lastSyncedText ?? '-'

  const handlePatientLabelClick = () => {
    if (shouldNavigateToPatientRegistration) {
      navigate('/patient')
    }
  }

  const handlePatientLabelKeyDown = (event) => {
    if (
      shouldNavigateToPatientRegistration &&
      (event.key === 'Enter' || event.key === ' ')
    ) {
      event.preventDefault()
      navigate('/patient')
    }
  }

  return (
    <header className="top-header">
      <div className="top-header__title-group">
        <h1 className="top-header__title">복약 모니터링 대시보드</h1>
        <p
          className="top-header__subtitle"
          role={shouldNavigateToPatientRegistration ? 'button' : undefined}
          tabIndex={shouldNavigateToPatientRegistration ? 0 : undefined}
          onClick={handlePatientLabelClick}
          onKeyDown={handlePatientLabelKeyDown}
        >
          {resolvedPatientLabel}
        </p>
      </div>

      <div className="top-header__right">
        <div className="top-header__device">
          <div
            className={`top-header__device-icon ${resolvedDeviceStatusClass}`}
            aria-hidden="true"
          >
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
            <p className={`top-header__device-status ${resolvedDeviceStatusClass}`}>
              {resolvedDeviceStatusText}
            </p>
            <p className="top-header__device-time">
              마지막 동기화: {resolvedLastSyncedText}
            </p>
          </div>
        </div>

        <div className="top-header__divider" />

        <div className="top-header__guardian">
          <div className="top-header__guardian-avatar" aria-hidden="true">
            {shouldShowProfileImg ? (
              <img
                className="top-header__guardian-avatar-img"
                src={resolvedProfileImg}
                alt=""
                onError={() => setFailedProfileImg(resolvedProfileImg)}
              />
            ) : (
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
            )}
          </div>
          <div>
            <p className="top-header__guardian-role">보호자</p>
            <p className="top-header__guardian-name">{resolvedGuardianName}</p>
          </div>
        </div>
      </div>
    </header>
  )
}

function shouldReuseCachedHeader() {
  return Boolean(cachedHeaderData) && cachedHeaderToken === getStoredToken()
}

async function loadSharedHeaderData() {
  const token = getStoredToken()

  if (!token) {
    return null
  }

  if (cachedHeaderData && cachedHeaderToken === token) {
    return cachedHeaderData
  }

  if (cachedHeaderPromise && cachedHeaderToken === token) {
    return cachedHeaderPromise
  }

  cachedHeaderToken = token
  cachedHeaderPromise = requestJson('/api/dashboard', { auth: true })
    .then((response) => {
      const headerData = mapSharedHeaderData(response?.data)
      cachedHeaderData = headerData
      return headerData
    })
    .finally(() => {
      cachedHeaderPromise = null
    })

  return cachedHeaderPromise
}

function mapSharedHeaderData(dashboardData) {
  const status = getDeviceStatus(dashboardData?.device)
  const guardianName = resolveGuardianName(
    dashboardData?.patient?.guardian_name,
    dashboardData?.member?.nick,
    '-',
  )

  return {
    patientLabel: buildPatientLabel(
      dashboardData?.patient,
      dashboardData?.patient_name,
    ),
    guardianName,
    profileImg: dashboardData?.member?.profile_img || dashboardData?.profile_img || '',
    deviceStatusText: getDeviceStatusText(status),
    deviceStatusClass: getDeviceStatusClass(status),
    lastSyncedText: formatHeaderRelativeTime(dashboardData?.device?.last_sync_time),
  }
}

function resolveGuardianName(guardianName, nick, fallbackName) {
  return (
    resolveDisplayName(guardianName) ||
    resolveDisplayName(nick) ||
    fallbackName
  )
}

function resolveDisplayName(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}

function buildPatientLabel(patient, fallbackName) {
  const patientName =
    resolveDisplayName(patient?.patient_name) ||
    resolveDisplayName(fallbackName) ||
    PATIENT_REGISTRATION_LABEL
  const patientAge = calculateAgeFromBirthdate(patient?.birthdate)

  return patientAge === null
    ? `환자: ${patientName}`
    : `환자: ${patientName} · 만 ${patientAge}세`
}

function calculateAgeFromBirthdate(value) {
  if (!value) {
    return null
  }

  const birthdate = new Date(value)

  if (Number.isNaN(birthdate.getTime())) {
    return null
  }

  const today = new Date()
  let age = today.getFullYear() - birthdate.getFullYear()
  const monthDiff = today.getMonth() - birthdate.getMonth()
  const dayDiff = today.getDate() - birthdate.getDate()

  if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
    age -= 1
  }

  return age >= 0 ? age : null
}

function formatHeaderRelativeTime(value) {
  if (!value) {
    return '-'
  }

  const target = new Date(value)

  if (Number.isNaN(target.getTime())) {
    return '-'
  }

  const diffMinutes = Math.max(
    0,
    Math.floor((Date.now() - target.getTime()) / 60000),
  )

  if (diffMinutes < 1) {
    return '방금 전'
  }

  if (diffMinutes < 60) {
    return `${diffMinutes}분 전`
  }

  const diffHours = Math.floor(diffMinutes / 60)

  if (diffHours < 24) {
    return `${diffHours}시간 전`
  }

  return `${Math.floor(diffHours / 24)}일 전`
}

function clearTopHeaderCache() {
  cachedHeaderToken = ''
  cachedHeaderData = null
  cachedHeaderPromise = null
}

export default TopHeader
