import { useEffect, useMemo, useState } from 'react'
import ScheduleAddModal from '../components/schedule/ScheduleAddModal'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import ScheduleHeader from '../components/schedule/ScheduleHeader'
import MonthlyCalendar from '../components/schedule/MonthlyCalendar'
import ScheduleSummaryCard from '../components/schedule/ScheduleSummaryCard'
import ScheduleList from '../components/schedule/ScheduleList'
import ScheduleInfoBanner from '../components/schedule/ScheduleInfoBanner'
import { hasStoredToken, requestJson } from '../api'
import '../styles/SchedulePage.css'
import '../styles/MobileBottomNav.css'

const SCHEDULE_INFO_BANNER = {
  title: '일정 안내',
  description: '백엔드에 저장된 복약 일정이 달력과 목록에 표시됩니다.',
}

function SchedulePage() {
  const [calendarState, setCalendarState] = useState(createInitialCalendarState)
  const [schedules, setSchedules] = useState([])
  const [medicationMap, setMedicationMap] = useState({})
  const [backendCompletedKeys, setBackendCompletedKeys] = useState(new Set())
  const [savingScheduleIds, setSavingScheduleIds] = useState(new Set())
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  const { year, month, selectedDate } = calendarState

  useEffect(() => {
    const fetchScheduleData = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const [scheduleData, medicationData, activityData] = await Promise.all([
          requestJson('/api/schedule', { auth: true }),
          requestJson('/api/medication'),
          requestJson('/api/log', { auth: true }),
        ])

        setSchedules(Array.isArray(scheduleData?.schedules) ? scheduleData.schedules : [])
        setMedicationMap(buildMedicationMap(medicationData?.data))
        setBackendCompletedKeys(buildCompletedKeySet(activityData?.activities))
      } catch (error) {
        console.error('schedule fetch error:', error)
      }
    }

    fetchScheduleData()
  }, [])

  const scheduleMap = useMemo(
    () => buildScheduleMap(schedules, medicationMap, backendCompletedKeys, year, month),
    [schedules, medicationMap, backendCompletedKeys, year, month],
  )

  const selectedSchedules = useMemo(
    () => scheduleMap[selectedDate] || [],
    [scheduleMap, selectedDate],
  )

  const completedCount = selectedSchedules.filter(
    (item) => item.status === 'done',
  ).length
  const totalCount = selectedSchedules.length
  const progressPercent =
    totalCount === 0 ? 0 : Math.round((completedCount / totalCount) * 100)

  const selectedDateLabel = formatSelectedDateLabel(selectedDate)

  const handleSelectDate = (dateKey) => {
    setCalendarState((prev) => ({
      ...prev,
      selectedDate: dateKey,
    }))
  }

  const handleChangeMonth = (diff) => {
    const nextDate = new Date(year, month - 1 + diff, 1)
    const nextYear = nextDate.getFullYear()
    const nextMonth = nextDate.getMonth() + 1

    const firstScheduledDate = findFirstScheduledDateInMonth(
      scheduleMap,
      nextYear,
      nextMonth,
    )

    setCalendarState({
      year: nextYear,
      month: nextMonth,
      selectedDate:
        firstScheduledDate || formatDateKey(nextYear, nextMonth, 1),
    })
  }

  const handleToggleSchedule = async (dateKey, item) => {
    if (!hasStoredToken()) {
      return
    }

    if (
      isCompletedSchedule(item.id, backendCompletedKeys) ||
      savingScheduleIds.has(item.id)
    ) {
      return
    }

    setSavingScheduleIds((prev) => {
      const next = new Set(prev)
      next.add(item.id)
      return next
    })

    try {
      await requestJson('/api/log', {
        method: 'POST',
        auth: true,
        body: {
          sche_id: item.sche_id,
          sche_time: buildScheduleDateTime(dateKey, item.time_to_take),
          status: 'SUCCESS',
        },
      })

      setBackendCompletedKeys((prev) => {
        const next = new Set(prev)
        next.add(item.id)
        return next
      })
    } catch (error) {
      console.error('schedule completion save error:', error)
      alert(error.message || '복약 완료 저장에 실패했습니다.')
    } finally {
      setSavingScheduleIds((prev) => {
        const next = new Set(prev)
        next.delete(item.id)
        return next
      })
    }
  }

  const handleCreateSchedule = async (newSchedule) => {
    if (!hasStoredToken()) {
      return
    }

    try {
      let resolvedMediId = Number(newSchedule.medi_id)

      if (!Number.isFinite(resolvedMediId) || resolvedMediId <= 0) {
        const medicationData = await requestJson(
          `/api/medication/search?keyword=${encodeURIComponent(newSchedule.medi_name)}`,
        )
        const matchedMedication = findMatchedMedication(
          medicationData?.data,
          newSchedule.medi_name,
        )

        if (!matchedMedication) {
          alert('등록된 약 정보를 찾지 못했습니다.')
          return
        }

        resolvedMediId = Number(matchedMedication.medi_id)
      }

      await requestJson('/api/schedule', {
        method: 'POST',
        auth: true,
        body: {
          medi_id: resolvedMediId,
          time_to_take: ensureSeconds(newSchedule.time_to_take),
          start_date: newSchedule.start_date || selectedDate,
          end_date: newSchedule.end_date || null,
          dose_interval: newSchedule.repeatType === 'weekly' ? 7 : null,
          status: 'ACTIVE',
        },
      })

      const refreshedSchedules = await requestJson('/api/schedule', { auth: true })
      setSchedules(
        Array.isArray(refreshedSchedules?.schedules)
          ? refreshedSchedules.schedules
          : [],
      )
      setIsAddModalOpen(false)
      alert('복약 일정이 추가되었습니다.')
    } catch (error) {
      console.error('schedule create error:', error)
      alert(error.message || '복약 일정 추가에 실패했습니다.')
    }
  }

  return (
    <div className="schedule-page">
      <div className="schedule-layout">
        <Sidebar activeMenu="schedule" />

        <div className="schedule-main">
          <TopHeader />

          <main className="schedule-content">
            <ScheduleHeader onOpenAddModal={() => setIsAddModalOpen(true)} />

            <MonthlyCalendar
              year={year}
              month={month}
              selectedDate={selectedDate}
              scheduleMap={scheduleMap}
              onSelectDate={handleSelectDate}
              onPrevMonth={() => handleChangeMonth(-1)}
              onNextMonth={() => handleChangeMonth(1)}
            />

            <ScheduleSummaryCard
              selectedDateLabel={selectedDateLabel}
              totalCount={totalCount}
              completedCount={completedCount}
              progressPercent={progressPercent}
            />

            <ScheduleList
              schedules={selectedSchedules}
              selectedDate={selectedDate}
              onToggle={handleToggleSchedule}
            />

            <ScheduleInfoBanner info={SCHEDULE_INFO_BANNER} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="schedule" />

      {isAddModalOpen ? (
        <ScheduleAddModal
          selectedDateLabel={selectedDateLabel}
          onClose={() => setIsAddModalOpen(false)}
          onSubmit={handleCreateSchedule}
        />
      ) : null}
    </div>
  )
}

function createInitialCalendarState() {
  const today = new Date()

  return {
    year: today.getFullYear(),
    month: today.getMonth() + 1,
    selectedDate: formatDateKey(
      today.getFullYear(),
      today.getMonth() + 1,
      today.getDate(),
    ),
  }
}

function buildMedicationMap(medications = []) {
  return medications.reduce((acc, medication) => {
    acc[medication.medi_id] = medication.medi_name
    return acc
  }, {})
}

function buildCompletedKeySet(activities = []) {
  return new Set(
    activities
      .filter((activity) => String(activity.status).toUpperCase() === 'SUCCESS')
      .map((activity) => {
        const dateKey = toDateKey(activity.sche_time)
        return dateKey ? `${activity.sche_id}-${dateKey}` : null
      })
      .filter(Boolean),
  )
}

function buildScheduleMap(
  schedules,
  medicationMap,
  completionKeySet,
  year,
  month,
) {
  const mappedSchedules = {}
  const monthStart = new Date(year, month - 1, 1)
  const monthEnd = new Date(year, month, 0)

  schedules.forEach((schedule) => {
    const scheduleStart = parseDate(schedule.start_date)
    const scheduleEnd = parseDate(schedule.end_date || formatDateKey(year, month, monthEnd.getDate()))

    if (!scheduleStart || !scheduleEnd) {
      return
    }

    const visibleStart =
      scheduleStart.getTime() > monthStart.getTime() ? scheduleStart : monthStart
    const visibleEnd =
      scheduleEnd.getTime() < monthEnd.getTime() ? scheduleEnd : monthEnd

    if (visibleStart.getTime() > visibleEnd.getTime()) {
      return
    }

    const intervalDays =
      Number(schedule.dose_interval) > 0 ? Number(schedule.dose_interval) : 1

    for (
      let currentDate = new Date(visibleStart);
      currentDate.getTime() <= visibleEnd.getTime();
      currentDate.setDate(currentDate.getDate() + 1)
    ) {
      const diffDays = Math.floor(
        (stripTime(currentDate).getTime() - stripTime(scheduleStart).getTime()) /
          86400000,
      )

      if (diffDays < 0 || diffDays % intervalDays !== 0) {
        continue
      }

      const dateKey = formatDateKey(
        currentDate.getFullYear(),
        currentDate.getMonth() + 1,
        currentDate.getDate(),
      )
      const itemId = `${schedule.sche_id}-${dateKey}`

      if (!mappedSchedules[dateKey]) {
        mappedSchedules[dateKey] = []
      }

      mappedSchedules[dateKey].push({
        id: itemId,
        sche_id: schedule.sche_id,
        time_to_take: formatTime(schedule.time_to_take),
        medi_name:
          medicationMap[schedule.medi_id] || `약물 ${schedule.medi_id}`,
        doseText:
          intervalDays > 1 ? `${intervalDays}일 간격 복용` : '매일 복용',
        status: isCompletedSchedule(itemId, completionKeySet) ? 'done' : 'pending',
      })
    }
  })

  Object.values(mappedSchedules).forEach((items) => {
    items.sort((a, b) => a.time_to_take.localeCompare(b.time_to_take))
  })

  return mappedSchedules
}

function isCompletedSchedule(itemId, completionKeySet) {
  return completionKeySet.has(itemId)
}

function findMatchedMedication(medications = [], medi_name = '') {
  const trimmedName = medi_name.trim().toLowerCase()

  return (
    medications.find(
      (item) => String(item.medi_name).trim().toLowerCase() === trimmedName,
    ) || medications[0] || null
  )
}

function formatSelectedDateLabel(dateKey) {
  const [yearText, monthText, dayText] = dateKey.split('-')
  const date = new Date(
    Number(yearText),
    Number(monthText) - 1,
    Number(dayText),
  )

  const weekMap = ['일', '월', '화', '수', '목', '금', '토']
  const weekday = weekMap[date.getDay()]

  return `${Number(monthText)}월 ${Number(dayText)}일 (${weekday})`
}

function formatDateKey(year, month, day) {
  const monthText = String(month).padStart(2, '0')
  const dayText = String(day).padStart(2, '0')
  return `${year}-${monthText}-${dayText}`
}

function buildScheduleDateTime(dateKey, timeValue) {
  const [yearText, monthText, dayText] = dateKey.split('-')
  const [hours = '0', minutes = '0'] = String(timeValue || '').split(':')
  const date = new Date(
    Number(yearText),
    Number(monthText) - 1,
    Number(dayText),
    Number(hours),
    Number(minutes),
    0,
    0,
  )

  return date.toISOString()
}

function findFirstScheduledDateInMonth(scheduleMap, year, month) {
  const prefix = `${year}-${String(month).padStart(2, '0')}-`

  const matchedDates = Object.keys(scheduleMap)
    .filter((key) => key.startsWith(prefix))
    .sort()

  return matchedDates[0] || null
}

function parseDate(value) {
  if (!value) {
    return null
  }

  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : stripTime(date)
}

function stripTime(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function toDateKey(value) {
  if (!value) {
    return ''
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return formatDateKey(date.getFullYear(), date.getMonth() + 1, date.getDate())
}

function formatTime(value) {
  if (!value) {
    return '-'
  }

  return String(value).slice(0, 5)
}

function ensureSeconds(value) {
  if (!value) {
    return ''
  }

  return value.length === 5 ? `${value}:00` : value
}

export default SchedulePage
