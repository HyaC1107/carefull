import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function BarChartCard({ data }) {
  return (
    <section className="stats-chart-card stats-chart-card--large">
      <h3 className="stats-chart-card__title">월별 복약 성공률 추이</h3>

      <div className="stats-chart-card__body stats-chart-card__body--large">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} barCategoryGap={28}>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="#e5e7eb"
            />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 12, fill: '#6b7280' }}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 12, fill: '#6b7280' }}
            />
            <Tooltip />

            {/* 막대 순서도 복약 성공률 -> 미복용률 */}
            <Bar
              dataKey="success"
              name="복약 성공률 (%)"
              fill="#10b981"
              radius={[6, 6, 0, 0]}
            />
            <Bar
              dataKey="missed"
              name="미복용률 (%)"
              fill="#ef4444"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 범례를 직접 그려서 순서를 강제로 고정 */}
      <div className="stats-bar-legend">
        <div className="stats-bar-legend__item">
          <span
            className="stats-bar-legend__dot"
            style={{ backgroundColor: '#10b981' }}
          />
          <span className="stats-bar-legend__label">복약 성공률 (%)</span>
        </div>

        <div className="stats-bar-legend__item">
          <span
            className="stats-bar-legend__dot"
            style={{ backgroundColor: '#ef4444' }}
          />
          <span className="stats-bar-legend__label">미복용률 (%)</span>
        </div>
      </div>
    </section>
  )
}

export default BarChartCard