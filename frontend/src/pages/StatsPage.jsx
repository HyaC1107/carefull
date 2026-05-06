import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import StatsHeader from '../components/stats/StatsHeader'
import StatsSummaryGrid from '../components/stats/StatsSummaryGrid'
import BarChartCard from '../components/stats/BarChartCard'
import LineChartCard from '../components/stats/LineChartCard'
import PieChartCard from '../components/stats/PieChartCard'
import WeeklyInsightSection from '../components/stats/WeeklyInsightSection'
import {
  getDeviceStatus,
  getDeviceStatusClass,
  getDeviceStatusText,
  hasStoredToken,
  requestJson,
} from '../api'
import { useUnreadCount } from '../hooks/useUnreadCount'
import '../styles/StatsPage.css'
import '../styles/MobileBottomNav.css'

const PIE_COLORS = ['#10b981', '#0ea5e9', '#f59e0b', '#ef4444', '#8b5cf6']
const PATIENT_REGISTRATION_LABEL = '환자를 등록해주세요.'
const KST_TIME_ZONE = 'Asia/Seoul'

function StatsPage() {
  const unreadCount = useUnreadCount()
  const [activities, setActivities] = useState([])
  const [dashboardData, setDashboardData] = useState(null)
  const [dashboardSummary, setDashboardSummary] = useState(null)
  const [schedules, setSchedules] = useState([])

  useEffect(() => {
    const fetchStatsData = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const activityLogPath = buildRecentSixMonthActivityLogPath()
        const [activityData, dashboardData, scheduleData] =
          await Promise.all([
            requestJson(activityLogPath, { auth: true }),
            requestJson('/api/dashboard', { auth: true }),
            requestJson('/api/schedule', { auth: true }),
          ])

        setActivities(Array.isArray(activityData?.activities) ? activityData.activities : [])
        setDashboardData(dashboardData?.data ?? null)
        setDashboardSummary(dashboardData?.data?.summary ?? null)
        setSchedules(Array.isArray(scheduleData?.schedules) ? scheduleData.schedules : [])
      } catch (error) {
        console.error('stats fetch error:', error)
      }
    }

    fetchStatsData()
  }, [])

  const statsSummaryCards = useMemo(
    () => buildStatsSummaryCards(dashboardSummary, activities, dashboardData?.statistics),
    [dashboardSummary, activities, dashboardData],
  )
  const monthlyTrendData = useMemo(
    () => buildMonthlyTrendData(activities, dashboardData?.statistics),
    [activities, dashboardData],
  )
  const timePatternData = useMemo(
    () => buildTimePatternData(activities),
    [activities],
  )
  const medicineRateData = useMemo(
    () => buildMedicineRateData(activities, schedules, dashboardData?.statistics),
    [activities, schedules, dashboardData],
  )
  const weeklyInsights = useMemo(
    () => buildWeeklyInsights(activities, dashboardData?.statistics),
    [activities, dashboardData],
  )
  const headerData = useMemo(
    () =>
      mapTopHeaderData({
        patient: dashboardData?.patient,
        patientName: dashboardData?.patient_name,
        device: dashboardData?.device,
        nick: dashboardData?.member?.nick,
        profileImg:
          dashboardData?.member?.profile_img || dashboardData?.profile_img || '',
      }),
    [dashboardData],
  )

  return (
    <div className="stats-page">
      <div className="stats-layout">
        <Sidebar activeMenu="stats" alertCount={unreadCount} />

        <div className="stats-main">
          <TopHeader
            patientLabel={headerData.patientLabel}
            guardianName={headerData.guardianName}
            profileImg={headerData.profileImg}
            deviceStatusText={headerData.deviceStatusText}
            deviceStatusClass={headerData.deviceStatusClass}
            lastSyncedText={headerData.lastSyncedText}
          />

          <main className="stats-content">
            <StatsHeader />
            <StatsSummaryGrid cards={statsSummaryCards} />
            <BarChartCard data={monthlyTrendData} />

            <section className="stats-chart-grid">
              <LineChartCard data={timePatternData} />
              <PieChartCard data={medicineRateData} />
            </section>

            <WeeklyInsightSection insights={weeklyInsights} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="stats" />
    </div>
  )
}

function buildRecentSixMonthActivityLogPath() {
  const today = getKstDateParts()
  const from = shiftKstMonth(today, -5)
  const params = new URLSearchParams({
    from: formatDateQueryValue({ ...from, day: 1 }),
    to: formatDateQueryValue(today),
  })

  // Stats activity-derived charts, including medication rate, use this six-month window.
  return `/api/log?${params.toString()}`
}

function formatDateQueryValue(date) {
  const parts = date instanceof Date ? getKstDateParts(date) : date

  if (!parts) {
    return ''
  }

  const year = parts.year
  const month = String(parts.month).padStart(2, '0')
  const day = String(parts.day).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function mapTopHeaderData({ patient, patientName, device, nick, profileImg }) {
  const status = getDeviceStatus(device)

  return {
    patientLabel: buildPatientLabel(patient, patientName),
    guardianName: resolveGuardianName(patient?.guardian_name, nick, '-'),
    profileImg,
    deviceStatusText: getDeviceStatusText(status),
    deviceStatusClass: getDeviceStatusClass(status),
    lastSyncedText: formatRelativeTime(device?.last_sync_time),
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

function buildStatsSummaryCards(summary, activities, statistics) {
  const lastSevenDays = getActivitiesWithinDays(activities, 7)
  const weeklyCompleted = statistics?.weekly?.success_count ?? lastSevenDays.filter(isSuccessStatus).length
  const weeklyMissed = statistics?.weekly
    ? Number(statistics.weekly.missed_count || 0) + Number(statistics.weekly.failed_count || 0)
    : lastSevenDays.filter(isMissedStatus).length

  return [
    {
      id: 'today-success-rate',
      title: '오늘 복약 성공률',
      value: `${summary?.today_success_rate ?? 0}%`,
      subText: `오늘 완료 ${summary?.today_completed_count ?? 0}건`,
      trendText: '',
      type: 'success',
    },
    {
      id: 'today-total-scheduled',
      title: '오늘 예정 복약',
      value: String(summary?.today_total_scheduled_count ?? 0),
      subText: '백엔드 기준 등록 일정',
      trendText: '',
      type: 'primary',
    },
    {
      id: 'weekly-completed',
      title: '최근 7일 완료',
      value: String(weeklyCompleted),
      subText: '성공 기록 기준',
      trendText: '',
      type: 'mint',
    },
    {
      id: 'weekly-missed',
      title: '최근 7일 미복용',
      value: String(weeklyMissed),
      subText: '실패/미복용 포함',
      trendText: '',
      type: 'growth',
    },
  ]
}

function buildMonthlyTrendData(activities, statistics) {
  if (Array.isArray(statistics?.monthly_trend) && statistics.monthly_trend.length > 0) {
    return statistics.monthly_trend.map((bucket) => ({
      month: bucket.month || `${Number(String(bucket.month_key || bucket.key || '').slice(5, 7))}월`,
      success: Number(bucket.success_rate) || 0,
      missed: Number(bucket.missed_rate) || 0,
      planned_count: Number(bucket.planned_count) || 0,
      success_count: Number(bucket.success_count) || 0,
      missed_count: Number(bucket.missed_count) || 0,
      failed_count: Number(bucket.failed_count) || 0,
    }))
  }

  const monthBuckets = getRecentMonthBuckets(6)

  activities.forEach((activity) => {
    const date = new Date(activity.sche_time || activity.created_at)

    if (Number.isNaN(date.getTime())) {
      return
    }

    const dateParts = getKstDateParts(date)

    if (!dateParts) {
      return
    }

    const bucketKey = getKstMonthBucketKey(dateParts)
    const bucket = monthBuckets.find((item) => item.key === bucketKey)

    if (!bucket) {
      return
    }

    bucket.total += 1

    if (isSuccessStatus(activity)) {
      bucket.successCount += 1
    }

    if (isMissedStatus(activity)) {
      bucket.missedCount += 1
    }
  })

  return monthBuckets.map((bucket) => ({
    month: `${bucket.month}월`,
    success:
      bucket.total === 0
        ? 0
        : Math.round((bucket.successCount / bucket.total) * 100),
    missed:
      bucket.total === 0
        ? 0
        : Math.round((bucket.missedCount / bucket.total) * 100),
  }))
}

function buildTimePatternData(activities) {
  const buckets = [
    { label: '새벽', start: 0, end: 5, count: 0 },
    { label: '아침', start: 6, end: 10, count: 0 },
    { label: '점심', start: 11, end: 14, count: 0 },
    { label: '오후', start: 15, end: 17, count: 0 },
    { label: '저녁', start: 18, end: 21, count: 0 },
    { label: '야간', start: 22, end: 23, count: 0 },
  ]

  getActivitiesWithinDays(activities, 30)
    .filter(isSuccessStatus)
    .forEach((activity) => {
      const date = new Date(activity.actual_time || activity.sche_time)

      if (Number.isNaN(date.getTime())) {
        return
      }

      const dateParts = getKstDateParts(date)

      if (!dateParts) {
        return
      }

      const hour = dateParts.hour
      const bucket = buckets.find((item) => hour >= item.start && hour <= item.end)

      if (bucket) {
        bucket.count += 1
      }
    })

  return buckets.map((bucket) => ({
    time: bucket.label,
    count: bucket.count,
  }))
}

function buildMedicineRateData(activities, schedules, statistics) {
  if (Array.isArray(statistics?.medication_rates) && statistics.medication_rates.length > 0) {
    return statistics.medication_rates.map((stat, index) => ({
      name: stat.medi_name || `약물 ${stat.medi_id}`,
      value: Number(stat.success_rate) || 0,
      fill: PIE_COLORS[index % PIE_COLORS.length],
      planned_count: Number(stat.planned_count) || 0,
      success_count: Number(stat.success_count) || 0,
      missed_count: Number(stat.missed_count) || 0,
      failed_count: Number(stat.failed_count) || 0,
    }))
  }

  const scheduleMedicationMap = schedules.reduce((acc, schedule) => {
    acc[schedule.sche_id] = {
      medi_id: schedule.medi_id,
      medi_name: schedule.medi_name,
    }
    return acc
  }, {})

  const medicationStats = {}

  activities.forEach((activity) => {
    const medication = scheduleMedicationMap[activity.sche_id]

    if (!medication?.medi_id) {
      return
    }

    const medicationId = medication.medi_id

    if (!medicationStats[medicationId]) {
      medicationStats[medicationId] = {
        name: medication.medi_name || `약물 ${medicationId}`,
        total: 0,
        success: 0,
      }
    }

    medicationStats[medicationId].total += 1

    if (isSuccessStatus(activity)) {
      medicationStats[medicationId].success += 1
    }
  })

  return Object.entries(medicationStats)
    .map(([medicationId, stat], index) => ({
      name: stat.name || `약물 ${medicationId}`,
      value: stat.total === 0 ? 0 : Math.round((stat.success / stat.total) * 100),
      fill: PIE_COLORS[index % PIE_COLORS.length],
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5)
}

function buildWeeklyInsights(activities, statistics) {
  if (statistics?.weekly) {
    const weekly = statistics.weekly
    const bestDay = getBestCompletionDay(
      getActivitiesWithinDays(activities, 7).filter(isSuccessStatus),
    )
    return [
      {
        id: 'weekly-success',
        label: '주간 성공 기록',
        value: `${weekly.success_count ?? 0}건`,
        subText: '최근 7일 성공 복약 수',
        type: 'success',
      },
      {
        id: 'weekly-missed',
        label: '주간 미복약 기록',
        value: `${Number(weekly.missed_count || 0) + Number(weekly.failed_count || 0)}건`,
        subText: '실패 및 미복약 포함',
        type: 'primary',
      },
      {
        id: 'weekly-rate',
        label: '주간 성공률',
        value: `${weekly.success_rate ?? 0}%`,
        subText: '최근 7일 활동 기준',
        type: 'mint',
      },
      {
        id: 'weekly-best-day',
        label: '가장 많은 복약일',
        value: bestDay.label,
        subText: `${bestDay.count}건 완료`,
        type: 'growth',
      },
    ]
  }

  const lastSevenDays = getActivitiesWithinDays(activities, 7)
  const completed = lastSevenDays.filter(isSuccessStatus)
  const missed = lastSevenDays.filter(isMissedStatus)
  const total = lastSevenDays.length
  const successRate = total === 0 ? 0 : Math.round((completed.length / total) * 100)
  const bestDay = getBestCompletionDay(completed)

  return [
    {
      id: 'weekly-success',
      label: '주간 성공 기록',
      value: `${completed.length}건`,
      subText: '최근 7일 성공 복약 수',
      type: 'success',
    },
    {
      id: 'weekly-missed',
      label: '주간 미복용 기록',
      value: `${missed.length}건`,
      subText: '실패 및 미복용 포함',
      type: 'primary',
    },
    {
      id: 'weekly-rate',
      label: '주간 성공률',
      value: `${successRate}%`,
      subText: '최근 7일 활동 기준',
      type: 'mint',
    },
    {
      id: 'weekly-best-day',
      label: '가장 많은 복약일',
      value: bestDay.label,
      subText: `${bestDay.count}건 완료`,
      type: 'growth',
    },
  ]
}

function getActivitiesWithinDays(activities, days) {
  const threshold = Date.now() - days * 86400000

  return activities.filter((activity) => {
    const date = new Date(activity.sche_time || activity.created_at)
    return !Number.isNaN(date.getTime()) && date.getTime() >= threshold
  })
}

function getRecentMonthBuckets(count) {
  const now = getKstDateParts()
  const buckets = []

  for (let index = count - 1; index >= 0; index -= 1) {
    const date = shiftKstMonth(now, -index)

    buckets.push({
      key: getKstMonthBucketKey(date),
      month: date.month,
      total: 0,
      successCount: 0,
      missedCount: 0,
    })
  }

  return buckets
}

function getBestCompletionDay(activities) {
  if (!activities.length) {
    return {
      label: '-',
      count: 0,
    }
  }

  const dayMap = activities.reduce((acc, activity) => {
    const date = new Date(activity.actual_time || activity.sche_time)

    if (Number.isNaN(date.getTime())) {
      return acc
    }

    const dateParts = getKstDateParts(date)

    if (!dateParts) {
      return acc
    }

    const key = `${dateParts.month}. ${dateParts.day}.`

    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})

  const [label, count] =
    Object.entries(dayMap).sort((a, b) => b[1] - a[1])[0] || []

  return {
    label: label || '-',
    count: count || 0,
  }
}

function getKstDateParts(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value)

  if (Number.isNaN(date.getTime())) {
    return null
  }

  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: KST_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    hourCycle: 'h23',
  })
  const parts = formatter.formatToParts(date)
  const getPart = (type) => Number(parts.find((part) => part.type === type)?.value)

  return {
    year: getPart('year'),
    month: getPart('month'),
    day: getPart('day'),
    hour: getPart('hour'),
  }
}

function shiftKstMonth(parts, diff) {
  const monthIndex = parts.year * 12 + (parts.month - 1) + diff
  const year = Math.floor(monthIndex / 12)
  const month = (monthIndex % 12) + 1

  return {
    year,
    month,
    day: parts.day,
    hour: parts.hour,
  }
}

function getKstMonthBucketKey(parts) {
  return `${parts.year}-${parts.month - 1}`
}

function isSuccessStatus(activity) {
  return ['SUCCESS', 'COMPLETED', 'TAKEN'].includes(
    String(activity?.status || '').toUpperCase(),
  )
}

function isMissedStatus(activity) {
  return ['MISSED', 'FAILED', 'ERROR'].includes(
    String(activity?.status || '').toUpperCase(),
  )
}

export default StatsPage
