import { useMemo, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import AlertsHeader from '../components/alerts/AlertsHeader'
import AlertFilterTabs from '../components/alerts/AlertFilterTabs'
import AlertListCard from '../components/alerts/AlertListCard'
import AlertsInfoBanner from '../components/alerts/AlertsInfoBanner'
import { alertsInfoBanner, initialAlerts } from '../data/alertsMock'
import '../styles/AlertsPage.css'
import '../styles/MobileBottomNav.css'

function AlertsPage() {
  const [activeFilter, setActiveFilter] = useState('all')
  const [alerts, setAlerts] = useState(initialAlerts)

  const tabs = useMemo(() => {
    const completedCount = alerts.filter((item) => item.type === 'completed').length
    const warningCount = alerts.filter((item) => item.type === 'warning').length
    const missedCount = alerts.filter((item) => item.type === 'missed').length

    return [
      { key: 'all', label: '전체', count: alerts.length },
      { key: 'completed', label: '복약 완료', count: completedCount },
      { key: 'warning', label: '주의', count: warningCount },
      { key: 'missed', label: '미복용', count: missedCount },
    ]
  }, [alerts])

  const filteredAlerts = useMemo(() => {
    if (activeFilter === 'all') return alerts
    return alerts.filter((item) => item.type === activeFilter)
  }, [alerts, activeFilter])

  const unreadCount = alerts.filter((item) => !item.isRead).length

  const handleMarkAllRead = () => {
    setAlerts((prev) =>
      prev.map((item) => ({
        ...item,
        isRead: true,
      })),
    )
  }

  return (
    <div className="alerts-page">
      <div className="alerts-layout">
        <Sidebar activeMenu="alerts" alertCount={unreadCount} />

        <div className="alerts-main">
          <TopHeader />

          <main className="alerts-content">
            <AlertsHeader />

            <AlertFilterTabs
              activeFilter={activeFilter}
              tabs={tabs}
              onChangeFilter={setActiveFilter}
            />

            <AlertListCard
              alerts={filteredAlerts}
              totalCount={filteredAlerts.length}
              onMarkAllRead={handleMarkAllRead}
            />

            <AlertsInfoBanner info={alertsInfoBanner} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="alerts" />
    </div>
  )
}

export default AlertsPage