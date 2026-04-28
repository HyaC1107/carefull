import ScheduleItemCard from './ScheduleItemCard'

// 일정 목록 전체 담당
function ScheduleList({ schedules, selectedDate, onToggle }) {
  if (!schedules.length) {
    return (
      <section className="schedule-list schedule-list--empty">
        <p className="schedule-list__empty-title">등록된 복약 일정이 없습니다.</p>
        <p className="schedule-list__empty-subtitle">
          다른 날짜를 선택하거나 새 복약 일정을 추가해보세요.
        </p>
      </section>
    )
  }

  return (
    <section className="schedule-list">
      {schedules.map((item) => (
        <ScheduleItemCard
          key={item.id}
          item={item}
          onToggle={() => onToggle(selectedDate, item)}
        />
      ))}
    </section>
  )
}

export default ScheduleList
