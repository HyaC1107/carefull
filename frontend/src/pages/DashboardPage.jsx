
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import SummaryCard from '../components/dashboard/SummaryCard'
import DeviceStatusSection from '../components/dashboard/DeviceStatusSection'
import AlertsSection from '../components/dashboard/AlertsSection'
import NextMedicationBanner from '../components/dashboard/NextMedicationBanner'
import {
  deviceStatus,
  nextMedication,
  recentAlerts,
  summaryCards,
} from '../data/dashboardMock'
import '../styles/DashboardPage.css'
import '../styles/MobileBottomNav.css'

// 이 파일은 "대시보드 페이지 전체를 조립"하는 역할만 담당합니다.
// 데스크톱에서는 Sidebar를 보여주고,
// 모바일에서는 CSS로 Sidebar를 숨긴 뒤 MobileBottomNav를 보여주게 됩니다.
function DashboardPage() {
  return (
    <div className="dashboard-page">
      <div className="dashboard-layout">
        {/* 데스크톱/큰 화면용 좌측 사이드바 */}
        <Sidebar activeMenu="dashboard" />

        {/* 오른쪽 메인 영역 */}
        <div className="dashboard-main">
          {/* 상단 헤더 */}
          <TopHeader />

          {/* 실제 본문 콘텐츠 */}
          <main className="dashboard-content">
            
            {/* 상단 요약 카드 4개 */}
            <section className="dashboard-summary-grid">
              {summaryCards.map((card) => (
                <SummaryCard
                  key={card.id}
                  title={card.title}
                  value={card.value}
                  subText={card.subText}
                  trendText={card.trendText}
                  type={card.type}
                />
              ))}
            </section>

            {/* 스마트 복약 디바이스 섹션 */}
            <DeviceStatusSection deviceStatus={deviceStatus} />

            {/* 최근 알림 섹션 */}
            <AlertsSection alerts={recentAlerts} />

            {/* 다음 복약 배너 */}
            <NextMedicationBanner nextMedication={nextMedication} />
          </main>
        </div>
      </div>

      {/* 모바일/태블릿 전용 하단 탭바 */}
      <MobileBottomNav activeMenu="dashboard" />
    </div>
  )
}

export default DashboardPage