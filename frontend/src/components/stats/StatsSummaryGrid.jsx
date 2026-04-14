import StatsSummaryCard from './StatsSummaryCard'

function StatsSummaryGrid({ cards }) {
  return (
    <section className="stats-summary-grid">
      {cards.map((card) => (
        <StatsSummaryCard
          key={card.id}
          title={card.title}
          value={card.value}
          subText={card.subText}
          trendText={card.trendText}
          type={card.type}
        />
      ))}
    </section>
  )
}

export default StatsSummaryGrid