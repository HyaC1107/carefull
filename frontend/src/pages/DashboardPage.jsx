import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import SummaryCard from '../components/dashboard/SummaryCard'
import DeviceStatusSection from '../components/dashboard/DeviceStatusSection'
import AlertsSection from '../components/dashboard/AlertsSection'
import NextMedicationBanner from '../components/dashboard/NextMedicationBanner'
import { hasStoredToken, requestJson } from '../api'
import '../styles/DashboardPage.css'
import '../styles/MobileBottomNav.css'

const DEFAULT_SUMMARY = {
  today_success_rate: 0,
  today_total_scheduled_count: 0,
  today_completed_count: 0,
  today_missed_count: 0,
  status_message: '데이터가 없습니다.',
}

const DEFAULT_DEVICE_STATUS = {
  connection_status: '-',
  medication_level: '-',
  last_sync_time: '-',
  next_schedule_time: '-',
}

const DEFAULT_NEXT_MEDICATION = {
  title: '다음 복약 일정이 없습니다.',
  description: '백엔드에서 예정된 복약 정보를 불러오면 여기에 표시됩니다.',
}
const PATIENT_REGISTRATION_LABEL = '환자를 등록해주세요.'

function DashboardPage() {
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    const fetchDashboardData = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const dashboardResponse = await requestJson('/api/dashboard', {
          auth: true,
        })

        console.log('dashboard response', dashboardResponse) // API 최종 응답 구조 확인

        setDashboardData(dashboardResponse?.data ?? null)
      } catch (error) {
        console.error('dashboard fetch error:', error)
      }
    }

    fetchDashboardData()
  }, [])

  useEffect(() => {
    console.log('dashboardData', dashboardData) // state에 실제로 무엇이 들어갔는지 확인
    console.log('patient path 1', dashboardData?.patient?.patient_name) // 중첩 patient.patient_name 경로 확인
    console.log('patient path 2', dashboardData?.patient_name) // 최상위 patient_name 경로 확인
  }, [dashboardData])

  const summaryCards = useMemo(
    () => buildSummaryCards(dashboardData?.summary),
    [dashboardData],
  )
  const deviceStatus = useMemo(
    () => mapDeviceStatus(dashboardData?.device),
    [dashboardData],
  )
  const recentAlerts = useMemo(
    () => mapDashboardAlerts(dashboardData?.recent_notifications),
    [dashboardData],
  )
  const nextMedication = useMemo(
    () =>
      mapNextMedication(
        dashboardData?.today_schedules,
        dashboardData?.device?.next_schedule_time,
      ),
    [dashboardData],
  )
  const patientLabel = buildPatientLabel(
    dashboardData?.patient,
    dashboardData?.patient_name,
  )
  const headerData = useMemo(
    () =>
      mapTopHeaderData({
        patient: dashboardData?.patient,
        device: dashboardData?.device,
        nick: dashboardData?.member?.nick,
        profileImg:
          dashboardData?.member?.profile_img || dashboardData?.profile_img || '',
      }),
    [dashboardData],
  )

  return (
    <div className="dashboard-page">
      <div className="dashboard-layout">
        <Sidebar activeMenu="dashboard" />

        <div className="dashboard-main">
          <TopHeader
            patientLabel={patientLabel}
            guardianName={headerData.guardianName}
            profileImg={headerData.profileImg}
            deviceStatusText={headerData.deviceStatusText}
            lastSyncedText={headerData.lastSyncedText}
          />

          <main className="dashboard-content">
            <section className="dashboard-summary-grid">
              {summaryCards.map((card) => (
                <SummaryCard
                  key={card.id}
                  title={card.title}
                  value={card.value}
                  subText={card.subText}
                  trendText={card.trendText}
                  type={card.type}
                />
              ))}
            </section>

            <DeviceStatusSection deviceStatus={deviceStatus} />
            <AlertsSection alerts={recentAlerts} />
            <NextMedicationBanner nextMedication={nextMedication} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="dashboard" />
    </div>
  )

}

function buildSummaryCards(summary = DEFAULT_SUMMARY) {
  return [
    {
      id: 'today-success-rate',
      title: '오늘 복약 성공률',
      value: `${summary?.today_success_rate ?? 0}%`,
      subText: summary?.status_message || '데이터가 없습니다.',
      trendText: '',
      type: 'success',
    },
    {
      id: 'today-total-schedules',
      title: '오늘 예정 복약',
      value: String(summary?.today_total_scheduled_count ?? 0),
      subText: '오늘 등록된 일정 수',
      trendText: '',
      type: 'schedule',
    },
    {
      id: 'today-completed',
      title: '오늘 완료 복약',
      value: String(summary?.today_completed_count ?? 0),
      subText: '복약 완료 건수',
      trendText: '',
      type: 'done',
    },
    {
      id: 'today-missed',
      title: '오늘 미복용',
      value: String(summary?.today_missed_count ?? 0),
      subText: '미복용 및 실패 건수',
      trendText: '',
      type: 'danger',
    },
  ]
}

function mapDeviceStatus(device) {
  if (!device) {
    return DEFAULT_DEVICE_STATUS
  }

  return {
    connection_status: device.is_connected ? '연결됨' : '연결 안 됨',
    medication_level:
      device.medication_level === null || device.medication_level === undefined
        ? '-'
        : `${device.medication_level}회`,
    last_sync_time: formatDateTime(device.last_sync_time),
    next_schedule_time: formatDateTime(device.next_schedule_time, true),
  }
}

function mapDashboardAlerts(notifications = []) {
  return notifications.map((notification) => ({
    id: notification.noti_id,
    label: getDashboardAlertLabel(notification.noti_type),
    type: getAlertType(notification.noti_type),
    timeAgo: formatRelativeTime(notification.created_at),
    message: notification.noti_msg || notification.noti_title || '',
  }))
}

function mapNextMedication(schedules = [], nextScheduleTime) {
  if (Array.isArray(schedules) && schedules.length > 0) {
    const nextSchedule =
      schedules.find((item) => item.status === 'Scheduled') || schedules[0]

    return {
      title: '다음 복약 예정',
      description: `${nextSchedule?.medi_name || '등록된 약물'} · ${formatTime(
        nextSchedule?.time_to_take || nextSchedule?.actual_time || nextScheduleTime,
      )}`,
    }
  }

  if (nextScheduleTime) {
    return {
      title: '다음 복약 예정',
      description: `${formatDateTime(nextScheduleTime, true)} 복약 일정이 있습니다.`,
    }
  }

  return DEFAULT_NEXT_MEDICATION
}

function mapTopHeaderData({ patient, device, nick, profileImg }) {
  return {
    guardianName: resolveGuardianName(patient?.guardian_name, nick, '-'),
    profileImg,
    deviceStatusText: getTopHeaderDeviceStatus(device?.is_connected),
    lastSyncedText: formatRelativeTime(device?.last_sync_time),
  }
}

function resolveGuardianName(guardianName, nick, fallbackName) {
  const normalizedGuardianName = normalizeDisplayName(guardianName)
  const normalizedNick = normalizeDisplayName(nick)

  return normalizedGuardianName || normalizedNick || fallbackName
}

function normalizeDisplayName(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}

function buildPatientLabel(patient, fallbackName) {
  const patientName =
    normalizeDisplayName(patient?.patient_name) ||
    normalizeDisplayName(fallbackName) ||
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

function getTopHeaderDeviceStatus(isConnected) {
  if (isConnected === true) {
    return '기기 연결됨'
  }

  if (isConnected === false) {
    return '기기 연결 안 됨'
  }

  return '기기 상태 확인 중'
}

function getDashboardAlertLabel(type) {
  switch (String(type || '').toUpperCase()) {
    case 'SUCCESS':
      return '복약 완료'
    case 'MISSED':
      return '미복용'
    default:
      return '주의'
  }
}

function getAlertType(type) {
  switch (String(type || '').toUpperCase()) {
    case 'SUCCESS':
      return 'completed'
    case 'MISSED':
      return 'missed'
    default:
      return 'warning'
  }
}

function formatDateTime(value, timeOnly = false) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return timeOnly ? String(value) : '-'
  }

  if (timeOnly) {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return date.toLocaleString('ko-KR', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatTime(value) {
  if (!value) {
    return '-'
  }

  if (String(value).includes('T')) {
    return formatDateTime(value, true)
  }

  return String(value).slice(0, 5)
}

function formatRelativeTime(value) {
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

export default DashboardPage
