import { createContext, useContext, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  getDeviceStatus,
  getDeviceStatusClass,
  getDeviceStatusText,
  hasStoredToken,
  requestJson,
} from '../api'

const HeaderDataContext = createContext(null)

export function HeaderDataProvider({ children }) {
  const [headerData, setHeaderData] = useState(null)
  const loadedForToken = useRef('')
  const location = useLocation()

  useEffect(() => {
    const token = hasStoredToken()
    if (!token || loadedForToken.current === token) return

    loadedForToken.current = String(token)

    requestJson('/api/dashboard', { auth: true })
      .then((res) => setHeaderData(mapHeaderData(res?.data)))
      .catch((err) => console.error('header data fetch error:', err))
  }, [])

  const refresh = () => {
    loadedForToken.current = ''
    if (!hasStoredToken()) return
    requestJson('/api/dashboard', { auth: true })
      .then((res) => setHeaderData(mapHeaderData(res?.data)))
      .catch((err) => console.error('header data refresh error:', err))
  }

  useEffect(() => {
    if (!hasStoredToken()) {
      loadedForToken.current = ''
      setHeaderData(null)
      return
    }

    refresh()
  }, [location.pathname])

  useEffect(() => {
    window.addEventListener('carefull:top-header-refresh', refresh)
    return () => window.removeEventListener('carefull:top-header-refresh', refresh)
  }, [])

  useEffect(() => {
    const applyDashboardData = (event) => {
      setHeaderData(mapHeaderData(event.detail))
    }

    window.addEventListener('carefull:top-header-data', applyDashboardData)
    return () => window.removeEventListener('carefull:top-header-data', applyDashboardData)
  }, [])

  return (
    <HeaderDataContext.Provider value={headerData}>
      {children}
    </HeaderDataContext.Provider>
  )
}

export function useHeaderData() {
  return useContext(HeaderDataContext)
}

function mapHeaderData(data) {
  const deviceStatus = getDeviceStatus(data?.device)

  return {
    patientLabel: buildPatientLabel(data?.patient),
    guardianName: data?.patient?.guardian_name || data?.member?.nick || '-',
    profileImg: data?.member?.profile_img || '',
    deviceStatusText: getDeviceStatusText(deviceStatus),
    deviceStatusClass: getDeviceStatusClass(deviceStatus),
    lastSyncedText: formatRelativeTime(data?.device?.last_sync_time),
  }
}

function buildPatientLabel(patient) {
  if (!patient?.patient_name) return '환자를 등록해주세요.'
  const age = calcAge(patient.birthdate)
  return age !== null
    ? `환자: ${patient.patient_name} · 만 ${age}세`
    : `환자: ${patient.patient_name}`
}

function calcAge(birthdate) {
  if (!birthdate) return null
  const birth = new Date(birthdate)
  if (isNaN(birth.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  ) age--
  return age >= 0 ? age : null
}

function formatRelativeTime(value) {
  if (!value) return '-'
  const diff = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000))
  if (diff < 1) return '방금 전'
  if (diff < 60) return `${diff}분 전`
  const h = Math.floor(diff / 60)
  if (h < 24) return `${h}시간 전`
  return `${Math.floor(h / 24)}일 전`
}
