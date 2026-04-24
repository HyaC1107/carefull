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
import { hasStoredToken, requestJson } from '../api'
import '../styles/StatsPage.css'
import '../styles/MobileBottomNav.css'

const PIE_COLORS = ['#10b981', '#0ea5e9', '#f59e0b', '#ef4444', '#8b5cf6']

function StatsPage() {
  const [activities, setActivities] = useState([])
  const [dashboardSummary, setDashboardSummary] = useState(null)
  const [schedules, setSchedules] = useState([])
  const [medicationMap, setMedicationMap] = useState({})

  useEffect(() => {
    const fetchStatsData = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const [activityData, dashboardData, scheduleData, medicationData] =
          await Promise.all([
            requestJson('/api/log', { auth: true }),
            requestJson('/api/dashboard', { auth: true }),
            requestJson('/api/schedule', { auth: true }),
            requestJson('/api/medication'),
          ])

        setActivities(Array.isArray(activityData?.activities) ? activityData.activities : [])
        setDashboardSummary(dashboardData?.data?.summary ?? null)
        setSchedules(Array.isArray(scheduleData?.schedules) ? scheduleData.schedules : [])
        setMedicationMap(buildMedicationMap(medicationData?.data))
      } catch (error) {
        console.error('stats fetch error:', error)
      }
    }

    fetchStatsData()
  }, [])

  const statsSummaryCards = useMemo(
    () => buildStatsSummaryCards(dashboardSummary, activities),
    [dashboardSummary, activities],
  )
  const monthlyTrendData = useMemo(
    () => buildMonthlyTrendData(activities),
    [activities],
  )
  const timePatternData = useMemo(
    () => buildTimePatternData(activities),
    [activities],
  )
  const medicineRateData = useMemo(
    () => buildMedicineRateData(activities, schedules, medicationMap),
    [activities, schedules, medicationMap],
  )
  const weeklyInsights = useMemo(
    () => buildWeeklyInsights(activities),
    [activities],
  )

  return (
    <div className="stats-page">
      <div className="stats-layout">
        <Sidebar activeMenu="stats" />

        <div className="stats-main">
          <TopHeader />

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

function buildMedicationMap(medications = []) {
  return medications.reduce((acc, medication) => {
    acc[medication.medi_id] = medication.medi_name
    return acc
  }, {})
}

function buildStatsSummaryCards(summary, activities) {
  const lastSevenDays = getActivitiesWithinDays(activities, 7)
  const weeklyCompleted = lastSevenDays.filter(isSuccessStatus).length
  const weeklyMissed = lastSevenDays.filter(isMissedStatus).length

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

function buildMonthlyTrendData(activities) {
  const monthBuckets = getRecentMonthBuckets(6)

  activities.forEach((activity) => {
    const date = new Date(activity.sche_time || activity.created_at)

    if (Number.isNaN(date.getTime())) {
      return
    }

    const bucketKey = `${date.getFullYear()}-${date.getMonth()}`
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

      const hour = date.getHours()
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

function buildMedicineRateData(activities, schedules, medicationMap) {
  const scheduleMedicationMap = schedules.reduce((acc, schedule) => {
    acc[schedule.sche_id] = schedule.medi_id
    return acc
  }, {})

  const medicationStats = {}

  activities.forEach((activity) => {
    const medicationId = scheduleMedicationMap[activity.sche_id]

    if (!medicationId) {
      return
    }

    if (!medicationStats[medicationId]) {
      medicationStats[medicationId] = {
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
      name: medicationMap[medicationId] || `약물 ${medicationId}`,
      value: stat.total === 0 ? 0 : Math.round((stat.success / stat.total) * 100),
      fill: PIE_COLORS[index % PIE_COLORS.length],
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5)
}

function buildWeeklyInsights(activities) {
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
  const now = new Date()
  const buckets = []

  for (let index = count - 1; index >= 0; index -= 1) {
    const date = new Date(now.getFullYear(), now.getMonth() - index, 1)

    buckets.push({
      key: `${date.getFullYear()}-${date.getMonth()}`,
      month: date.getMonth() + 1,
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

    const key = date.toLocaleDateString('ko-KR', {
      month: 'numeric',
      day: 'numeric',
    })

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

function isSuccessStatus(activity) {
  return String(activity?.status || '').toUpperCase() === 'SUCCESS'
}

function isMissedStatus(activity) {
  return ['MISSED', 'FAILED', 'ERROR'].includes(
    String(activity?.status || '').toUpperCase(),
  )
}

export default StatsPage
