import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import StatsHeader from '../components/stats/StatsHeader'
import StatsSummaryGrid from '../components/stats/StatsSummaryGrid'
import BarChartCard from '../components/stats/BarChartCard'
import LineChartCard from '../components/stats/LineChartCard'
import PieChartCard from '../components/stats/PieChartCard'
import WeeklyInsightSection from '../components/stats/WeeklyInsightSection'
import {
  medicineRateData,
  monthlyTrendData,
  statsSummaryCards,
  timePatternData,
  weeklyInsights,
} from '../data/statsMock'
import '../styles/StatsPage.css'
import '../styles/MobileBottomNav.css'

function StatsPage() {
  return (
    <div className="stats-page">
      <div className="stats-layout">
        <Sidebar activeMenu="stats" />

        <div className="stats-main">
          <TopHeader />

          <main className="stats-content">
            <StatsHeader />
            <StatsSummaryGrid cards={statsSummaryCards} />
            <BarChartCard data={monthlyTrendData} />

            <section className="stats-chart-grid">
              <LineChartCard data={timePatternData} />
              <PieChartCard data={medicineRateData} />
            </section>

            <WeeklyInsightSection insights={weeklyInsights} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="stats" />
    </div>
  )
}

export default StatsPage