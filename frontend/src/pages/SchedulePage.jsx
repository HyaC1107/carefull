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
import { useUnreadCount } from '../hooks/useUnreadCount'
import { hasStoredToken, requestJson } from '../api'
import '../styles/SchedulePage.css'
import '../styles/MobileBottomNav.css'

const SCHEDULE_INFO_BANNER = {
  title: '일정 안내',
  description: '저장된 복약 일정이 달력과 목록에 표시됩니다.',
}

function SchedulePage() {
  const unreadCount = useUnreadCount()
  const [calendarState, setCalendarState] = useState(createInitialCalendarState)
  const [schedules, setSchedules] = useState([])
  const [backendCompletedKeys, setBackendCompletedKeys] = useState(new Set())
  const [savingScheduleIds, setSavingScheduleIds] = useState(new Set())
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [deletingScheduleIds, setDeletingScheduleIds] = useState(new Set())

  const { year, month, selectedDate } = calendarState

  useEffect(() => {
    const fetchScheduleData = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const activityLogPath = buildMonthActivityLogPath(year, month)
        const [scheduleData, activityData] = await Promise.all([
          requestJson('/api/schedule', { auth: true }),
          requestJson(activityLogPath, { auth: true }),
        ])

        setSchedules(Array.isArray(scheduleData?.schedules) ? scheduleData.schedules : [])
        setBackendCompletedKeys(buildCompletedKeySet(activityData?.activities))
      } catch (error) {
        console.error('schedule fetch error:', error)
      }
    }

    fetchScheduleData()
  }, [month, year])

  const scheduleMap = useMemo(
    () => buildScheduleMap(schedules, backendCompletedKeys, year, month),
    [schedules, backendCompletedKeys, year, month],
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
  const todayDateKey = getTodayDateKey()

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
      window.dispatchEvent(new Event('carefull:top-header-refresh'))
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
      await requestJson('/api/schedule', {
        method: 'POST',
        auth: true,
        body: {
          medi_id: newSchedule.medi_id,
          medications: newSchedule.medications,
          time_to_take: ensureSeconds(newSchedule.time_to_take),
          time_to_take_list: Array.isArray(newSchedule.time_to_take_list)
            ? newSchedule.time_to_take_list.map(ensureSeconds)
            : undefined,
          start_date: newSchedule.start_date || selectedDate,
          end_date: newSchedule.end_date || newSchedule.start_date || selectedDate,
          dose_interval:
            newSchedule.repeatType === 'interval'
              ? Number(newSchedule.dose_interval)
              : null,
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

  const handleDeleteSchedule = async (item) => {
    if (!hasStoredToken() || !item?.sche_id) {
      return
    }

    const confirmed = window.confirm(
      '이 복약 일정을 삭제할까요?\n반복 일정인 경우 이후 날짜에서도 표시되지 않습니다.',
    )

    if (!confirmed) {
      return
    }

    setDeletingScheduleIds((prev) => {
      const next = new Set(prev)
      next.add(item.sche_id)
      return next
    })

    try {
      await requestJson(`/api/schedule/${item.sche_id}?date=${encodeURIComponent(selectedDate)}`, {
        method: 'DELETE',
        auth: true,
      })

      const refreshedSchedules = await requestJson('/api/schedule', { auth: true })
      setSchedules(
        Array.isArray(refreshedSchedules?.schedules)
          ? refreshedSchedules.schedules
          : [],
      )
      window.dispatchEvent(new Event('carefull:top-header-refresh'))
    } catch (error) {
      console.error('schedule delete error:', error)
      alert(error.message || '복약 일정 삭제에 실패했습니다.')
    } finally {
      setDeletingScheduleIds((prev) => {
        const next = new Set(prev)
        next.delete(item.sche_id)
        return next
      })
    }
  }

  return (
    <div className="schedule-page">
      <div className="schedule-layout">
        <Sidebar activeMenu="schedule" alertCount={unreadCount} />

        <div className="schedule-main">
          <TopHeader />

          <main className="schedule-content">
            <ScheduleHeader
              onOpenAddModal={() => setIsAddModalOpen(true)}
              onOpenDeleteModal={() => setIsDeleteModalOpen(true)}
            />

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
              isTodaySelected={selectedDate === todayDateKey}
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

      {isDeleteModalOpen ? (
        <ScheduleDeleteModal
          schedules={selectedSchedules}
          selectedDateLabel={selectedDateLabel}
          deletingScheduleIds={deletingScheduleIds}
          onClose={() => setIsDeleteModalOpen(false)}
          onDelete={handleDeleteSchedule}
        />
      ) : null}
    </div>
  )
}

function ScheduleDeleteModal({
  schedules,
  selectedDateLabel,
  deletingScheduleIds,
  onClose,
  onDelete,
}) {
  return (
    <div className="schedule-modal-overlay" onClick={onClose}>
      <div
        className="schedule-modal schedule-delete-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="schedule-modal__header">
          <div>
            <h3 className="schedule-modal__title">복약 일정 삭제</h3>
            <p className="schedule-modal__subtitle">
              {selectedDateLabel}의 복약 일정 중 삭제할 항목을 선택하세요
            </p>
          </div>

          <button
            type="button"
            className="schedule-modal__close-button"
            onClick={onClose}
          >
            x
          </button>
        </div>

        <div className="schedule-modal__body">
          {schedules.length > 0 ? (
            <div className="schedule-delete-modal__list">
              {schedules.map((item) => {
                const isDeleting = deletingScheduleIds.has(item.sche_id)

                return (
                  <div className="schedule-delete-modal__item" key={item.id}>
                    <div className="schedule-delete-modal__item-info">
                      <strong>{item.time_to_take}</strong>
                      <span>{item.medi_name}</span>
                      <small>{item.doseText}</small>
                    </div>
                    <button
                      type="button"
                      className="schedule-delete-modal__delete-button"
                      onClick={() => onDelete(item)}
                      disabled={isDeleting}
                    >
                      {isDeleting ? '삭제 중' : '삭제'}
                    </button>
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="schedule-delete-modal__empty">
              선택한 날짜에 삭제할 복약 일정이 없습니다.
            </p>
          )}

          <div className="schedule-modal__actions">
            <button
              type="button"
              className="schedule-modal__button schedule-modal__button--secondary"
              onClick={onClose}
            >
              닫기
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function createInitialCalendarState() {
  const today = getKstDateParts()

  return {
    year: today.year,
    month: today.month,
    selectedDate: formatDateKey(today.year, today.month, today.day),
  }
}

function getTodayDateKey() {
  const today = getKstDateParts()
  return formatDateKey(today.year, today.month, today.day)
}

function buildMonthActivityLogPath(year, month) {
  const lastDay = new Date(year, month, 0).getDate()
  const params = new URLSearchParams({
    from: formatDateKey(year, month, 1),
    to: formatDateKey(year, month, lastDay),
  })

  return `/api/log?${params.toString()}`
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

function buildScheduleMap(schedules, completionKeySet, year, month) {
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
        medi_name: schedule.medi_name || `약물 ${schedule.medi_id}`,
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
  const [hours = '00', minutes = '00', seconds = '00'] = String(timeValue || '')
    .split(':')

  return `${dateKey}T${hours.padStart(2, '0')}:${minutes.padStart(2, '0')}:${String(
    seconds || '00',
  ).padStart(2, '0')}`
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

function getKstDateParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const getPart = (type) => Number(parts.find((part) => part.type === type)?.value)

  return {
    year: getPart('year'),
    month: getPart('month'),
    day: getPart('day'),
  }
}

export default SchedulePage
