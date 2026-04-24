function WeeklyInsightCard({ label, value, subText, type }) {
  return (
    <article className={`weekly-insight-card weekly-insight-card--${type}`}>
      <p className="weekly-insight-card__label">{label}</p>
      <p className="weekly-insight-card__value">{value}</p>
      <p className="weekly-insight-card__subtext">{subText}</p>
    </article>
  )
}

export default WeeklyInsightCard