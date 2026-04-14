import CalendarDateCell from './CalendarDateCell'

function MonthlyCalendar({
  year,
  month,
  selectedDate,
  scheduleMap,
  onSelectDate,
  onPrevMonth,
  onNextMonth,
}) {
  const weekdayLabels = ['일', '월', '화', '수', '목', '금', '토']

  const firstDay = new Date(year, month - 1, 1).getDay()
  const lastDate = new Date(year, month, 0).getDate()

  const cells = []

  for (let i = 0; i < firstDay; i += 1) {
    cells.push(null)
  }

  for (let day = 1; day <= lastDate; day += 1) {
    cells.push(day)
  }

  // 뒤쪽 빈칸
  // 마지막 주가 7칸이 안 차면 남은 칸을 null로 채워서
  // 달력 모양이 항상 일정하게 보이도록 함
  const remainingCells = cells.length % 7 === 0 ? 0 : 7 - (cells.length % 7)

  for (let i = 0; i < remainingCells; i += 1) {
    cells.push(null)
  }

  return (
    <section className="schedule-calendar-card">
      <div className="schedule-calendar-card__top">
        <h3 className="schedule-calendar-card__title">
          {year}년 {month}월
        </h3>

        <div className="schedule-calendar-card__actions">
          <button
            type="button"
            className="schedule-calendar-card__nav-button"
            onClick={onPrevMonth}
          >
            ‹
          </button>
          <button
            type="button"
            className="schedule-calendar-card__nav-button"
            onClick={onNextMonth}
          >
            ›
          </button>
        </div>
      </div>

      <div className="schedule-calendar-card__weekdays">
        {weekdayLabels.map((label, index) => (
          <div
            key={label}
            className={`schedule-calendar-card__weekday ${
              index === 0 ? 'schedule-calendar-card__weekday--sunday' : ''
            } ${index === 6 ? 'schedule-calendar-card__weekday--saturday' : ''}`}
          >
            {label}
          </div>
        ))}
      </div>

      <div className="schedule-calendar-card__grid">
        {cells.map((day, index) => {
          if (!day) {
            return <CalendarDateCell key={`empty-${index}`} day={null} />
          }

          const dateKey = formatDateKey(year, month, day)
          const dateDay = new Date(year, month - 1, day).getDay()
          const hasSchedule = Boolean(scheduleMap[dateKey]?.length)
          const isSelected = selectedDate === dateKey

          return (
            <CalendarDateCell
              key={dateKey}
              day={day}
              isSelected={isSelected}
              hasSchedule={hasSchedule}
              isSunday={dateDay === 0}
              isSaturday={dateDay === 6}
              onClick={() => onSelectDate(dateKey)}
            />
          )
        })}
      </div>
    </section>
  )
}

function formatDateKey(year, month, day) {
  const monthText = String(month).padStart(2, '0')
  const dayText = String(day).padStart(2, '0')
  return `${year}-${monthText}-${dayText}`
}

export default MonthlyCalendar