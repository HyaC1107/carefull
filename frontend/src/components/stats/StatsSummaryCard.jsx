function StatsSummaryCard({ title, value, subText, trendText, type }) {
  return (
    <article className="stats-summary-card">
      <div className="stats-summary-card__top">
        <div
          className={`stats-summary-card__icon stats-summary-card__icon--${type}`}
          aria-hidden="true"
        >
          {renderSummaryIcon(type)}
        </div>

        {trendText ? (
          <span className="stats-summary-card__trend">↑ {trendText}</span>
        ) : null}
      </div>

      <p className="stats-summary-card__title">{title}</p>
      <p className={`stats-summary-card__value stats-summary-card__value--${type}`}>
        {value}
      </p>
      <p className="stats-summary-card__subtext">{subText}</p>
    </article>
  )
}

function renderSummaryIcon(type) {
  switch (type) {
    case 'success':
      return (
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      )

    case 'primary':
      return (
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="5" y="4" width="14" height="16" rx="2" />
          <path d="M9 2v4M15 2v4M8 10h8M8 14h5" />
        </svg>
      )

    case 'mint':
      return (
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 2" />
        </svg>
      )

    case 'growth':
      return (
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M4 16l5-5 4 4 7-7" />
          <path d="M20 10V4h-6" />
        </svg>
      )

    default:
      return null
  }
}

export default StatsSummaryCard