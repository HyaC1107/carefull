import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function LineChartCard({ data }) {
  return (
    <section className="stats-chart-card">
      <h3 className="stats-chart-card__title">시간대별 복약 패턴</h3>

      <div className="stats-chart-card__body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
            <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#6b7280' }} />
            <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#06b6d4"
              strokeWidth={3}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <p className="stats-chart-card__caption">
        최근 30일간 시간대별 복약 완료 횟수
      </p>
    </section>
  )
}

export default LineChartCard