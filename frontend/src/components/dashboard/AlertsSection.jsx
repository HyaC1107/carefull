import AlertItem from './AlertItem'

// 이 컴포넌트는 "최근 알림" 섹션 전체를 담당합니다.
// 실제 알림 카드 하나하나는 AlertItem에 위임합니다.
function AlertsSection({ alerts }) {
  return (
    <section className="dashboard-section">
      <h2 className="dashboard-section__title">최근 알림</h2>

      <div className="alerts-section__list">
        {alerts.map((alert) => (
          <AlertItem key={alert.id} alert={alert} />
        ))}
      </div>
    </section>
  )
}

export default AlertsSection