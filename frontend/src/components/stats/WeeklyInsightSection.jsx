import WeeklyInsightCard from './WeeklyInsightCard'

function WeeklyInsightSection({ insights }) {
  return (
    <section className="weekly-insight-section">
      <h3 className="weekly-insight-section__title">주간 상세 리포트</h3>

      <div className="weekly-insight-section__grid">
        {insights.map((item) => (
          <WeeklyInsightCard
            key={item.id}
            label={item.label}
            value={item.value}
            subText={item.subText}
            type={item.type}
          />
        ))}
      </div>
    </section>
  )
}

export default WeeklyInsightSection