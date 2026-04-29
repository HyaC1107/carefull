// 일정 카드 1개 담당
function ScheduleItemCard({ item, onToggle }) {
  const isDone = item.status === 'done'

  return (
    <article className="schedule-item-card">
      <div className="schedule-item-card__left">
        <div className="schedule-item-card__time-block">
          <span className="schedule-item-card__clock" aria-hidden="true">
            🕒
          </span>
          <span className="schedule-item-card__time">{item.time_to_take}</span>
        </div>

        <div className="schedule-item-card__info">
          <div className="schedule-item-card__title-row">
            <h4 className="schedule-item-card__medicine-name">{item.medi_name}</h4>
            <span
              className={`schedule-item-card__status-badge ${
                isDone
                  ? 'schedule-item-card__status-badge--done'
                  : 'schedule-item-card__status-badge--pending'
              }`}
            >
              {isDone ? '복용 완료' : '복용 전'}
            </span>
          </div>

          <p className="schedule-item-card__dose">{item.doseText}</p>
        </div>
      </div>

      <button
        type="button"
        className={`schedule-item-card__check-button ${
          isDone ? 'schedule-item-card__check-button--done' : ''
        }`}
        onClick={onToggle}
        aria-label="복약 완료 상태 변경"
      >
        {isDone ? '✓' : ''}
      </button>
    </article>
  )
}

export default ScheduleItemCard
