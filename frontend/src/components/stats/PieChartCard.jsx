import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

function PieChartCard({ data }) {
  return (
    <section className="stats-chart-card">
      <h3 className="stats-chart-card__title">약물별 복약률</h3>

      <div className="stats-chart-card__body">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={38}
              outerRadius={72}
              paddingAngle={2}
              labelLine={false}
              label={renderPieLabel}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="stats-pie-legend">
        {data.map((item) => (
          <div key={item.name} className="stats-pie-legend__item">
            <span
              className="stats-pie-legend__dot"
              style={{ backgroundColor: item.fill }}
            />
            <span className="stats-pie-legend__label">
              {item.name} {item.value}%
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}

function renderPieLabel({
  cx,
  cy,
  midAngle,
  outerRadius,
  name,
  value,
  fill,
}) {
  const RADIAN = Math.PI / 180
  const radius = outerRadius + 18
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  const textAnchor = x > cx ? 'start' : 'end'

  return (
    <text
      x={x}
      y={y}
      fill={fill}
      textAnchor={textAnchor}
      dominantBaseline="central"
      fontSize="11"
      fontWeight="700"
    >
      {`${name} ${value}%`}
    </text>
  )
}

export default PieChartCard