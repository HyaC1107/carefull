// 이 컴포넌트는 상단의 작은 요약 카드 1개를 담당합니다.
// 같은 카드 UI를 여러 번 재사용하기 위해 따로 분리했습니다.
function SummaryCard({ title, value, subText, trendText, type }) {
  return (
    <article className="summary-card">
      <div className="summary-card__top">
        <div className={`summary-card__icon summary-card__icon--${type}`} aria-hidden="true">
          {getSummaryIcon(type)}
        </div>

        {/* trendText가 있는 카드만 오른쪽 상단 증감 표시 */}
        {trendText ? <span className="summary-card__trend">↑ {trendText}</span> : null}
      </div>

      <p className="summary-card__title">{title}</p>
      <p className={`summary-card__value summary-card__value--${type}`}>{value}</p>
      <p className="summary-card__subtext">{subText}</p>
    </article>
  )
}

// 카드 타입에 따라 아이콘을 간단히 다르게 표시합니다.
function getSummaryIcon(type) {
  switch (type) {
    case 'success':
    case 'done':
      return '✓'
    case 'schedule':
      return '🗓'
    case 'danger':
      return '✕'
    default:
      return '•'
  }
}

export default SummaryCard