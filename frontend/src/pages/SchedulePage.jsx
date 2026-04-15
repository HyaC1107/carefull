import { useMemo, useState } from 'react'
import ScheduleAddModal from '../components/schedule/ScheduleAddModal'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import ScheduleHeader from '../components/schedule/ScheduleHeader'
import MonthlyCalendar from '../components/schedule/MonthlyCalendar'
import ScheduleSummaryCard from '../components/schedule/ScheduleSummaryCard'
import ScheduleList from '../components/schedule/ScheduleList'
import ScheduleInfoBanner from '../components/schedule/ScheduleInfoBanner'
import {
  initialScheduleMap,
  initialScheduleState,
  scheduleInfoBanner,
} from '../data/scheduleMock'
import '../styles/SchedulePage.css'
import '../styles/MobileBottomNav.css'

function SchedulePage() {
  const [calendarState, setCalendarState] = useState(initialScheduleState)
  const [scheduleMap, setScheduleMap] = useState(initialScheduleMap)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  const { year, month, selectedDate } = calendarState

  const selectedSchedules = useMemo(() => {
    return scheduleMap[selectedDate] || []
  }, [scheduleMap, selectedDate])

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

  const handleToggleSchedule = (dateKey, itemId) => {
    setScheduleMap((prev) => {
      const currentItems = prev[dateKey] || []

      const updatedItems = currentItems.map((item) => {
        if (item.id !== itemId) return item

        return {
          ...item,
          status: item.status === 'done' ? 'pending' : 'done',
        }
      })

      return {
        ...prev,
        [dateKey]: updatedItems,
      }
    })
  }

  return (
    <div className="schedule-page">
      <div className="schedule-layout">
        <Sidebar activeMenu="schedule" />

        <div className="schedule-main">
          <TopHeader />

          <main className="schedule-content">
            {/* 페이지 상단 제목/설명/추가 버튼 */}
            <ScheduleHeader onOpenAddModal={() => setIsAddModalOpen(true)} />

            {/* 핵심: 달력 카드 */}
            <MonthlyCalendar
              year={year}
              month={month}
              selectedDate={selectedDate}
              scheduleMap={scheduleMap}
              onSelectDate={handleSelectDate}
              onPrevMonth={() => handleChangeMonth(-1)}
              onNextMonth={() => handleChangeMonth(1)}
            />

            {/* 선택 날짜 요약 */}
            <ScheduleSummaryCard
              selectedDateLabel={selectedDateLabel}
              totalCount={totalCount}
              completedCount={completedCount}
              progressPercent={progressPercent}
            />

            {/* 일정 리스트 */}
            <ScheduleList
              schedules={selectedSchedules}
              selectedDate={selectedDate}
              onToggle={handleToggleSchedule}
            />

            {/* 하단 안내 배너 */}
            <ScheduleInfoBanner info={scheduleInfoBanner} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="schedule" />

      {isAddModalOpen ? (
        <ScheduleAddModal
          selectedDateLabel={selectedDateLabel}
          onClose={() => setIsAddModalOpen(false)}
          onSubmit={(newSchedule) => {
            console.log('새 복약 일정', newSchedule)
            setIsAddModalOpen(false)
            alert('복약 일정이 추가되었습니다.')
          }}
        />
      ) : null}
    </div>
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

function findFirstScheduledDateInMonth(scheduleMap, year, month) {
  const prefix = `${year}-${String(month).padStart(2, '0')}-`

  const matchedDates = Object.keys(scheduleMap)
    .filter((key) => key.startsWith(prefix))
    .sort()

  return matchedDates[0] || null
}

export default SchedulePage