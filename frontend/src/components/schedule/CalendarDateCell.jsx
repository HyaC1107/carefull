function CalendarDateCell({
  day,
  isSelected,
  hasSchedule,
  isSunday,
  isSaturday,
  onClick,
}) {
  if (!day) {
    return <div className="calendar-date-cell calendar-date-cell--empty" />
  }

  return (
    <button
      type="button"
      className={`calendar-date-cell ${isSelected ? 'calendar-date-cell--selected' : ''}`}
      onClick={onClick}
    >
      <span
        className={`calendar-date-cell__number ${
          isSunday ? 'calendar-date-cell__number--sunday' : ''
        } ${isSaturday ? 'calendar-date-cell__number--saturday' : ''}`}
      >
        {day}
      </span>

      {hasSchedule ? <span className="calendar-date-cell__dot" /> : null}
    </button>
  )
}

export default CalendarDateCell