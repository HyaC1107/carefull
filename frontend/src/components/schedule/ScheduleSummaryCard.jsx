// 선택한 날짜의 요약 정보 카드
function ScheduleSummaryCard({
  selectedDateLabel,
  totalCount,
  completedCount,
  progressPercent,
}) {
  return (
    <section className="schedule-summary-card">
      <div>
        <h3 className="schedule-summary-card__title">
          {selectedDateLabel}의 복약 일정
        </h3>
        <p className="schedule-summary-card__subtitle">
          총 {totalCount}개의 복약 일정 · 완료 {completedCount}개
        </p>
      </div>

      <div className="schedule-summary-card__progress-circle">
        <span className="schedule-summary-card__progress-value">
          {progressPercent}
        </span>
        <span className="schedule-summary-card__progress-label">%</span>
      </div>
    </section>
  )
}

export default ScheduleSummaryCard