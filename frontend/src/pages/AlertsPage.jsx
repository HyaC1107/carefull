import { useEffect, useMemo, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import AlertsHeader from '../components/alerts/AlertsHeader'
import AlertFilterTabs from '../components/alerts/AlertFilterTabs'
import AlertListCard from '../components/alerts/AlertListCard'
import AlertsInfoBanner from '../components/alerts/AlertsInfoBanner'
import { hasStoredToken, requestJson } from '../api'
import '../styles/AlertsPage.css'
import '../styles/MobileBottomNav.css'

const ALERTS_INFO = {
  title: '알림 안내',
  description: '백엔드에서 전달된 복약 알림만 표시됩니다.',
}

function AlertsPage() {
  const [activeFilter, setActiveFilter] = useState('all')
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    const fetchNotifications = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const data = await requestJson('/api/notification', { auth: true })
        setAlerts(mapNotifications(data?.notifications))
      } catch (error) {
        console.error('notification fetch error:', error)
      }
    }

    fetchNotifications()
  }, [])

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
    if (activeFilter === 'all') {
      return alerts
    }

    return alerts.filter((item) => item.type === activeFilter)
  }, [alerts, activeFilter])

  const unreadCount = alerts.filter((item) => !item.isRead).length

  const handleMarkAllRead = async () => {
    if (!hasStoredToken()) {
      return
    }

    try {
      await requestJson('/api/notification/read-all', {
        method: 'PATCH',
        auth: true,
      })

      setAlerts((prev) =>
        prev.map((item) => ({
          ...item,
          isRead: true,
        })),
      )
    } catch (error) {
      console.error('notification read-all error:', error)
    }
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

            <AlertsInfoBanner info={ALERTS_INFO} />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="alerts" />
    </div>
  )
}

function mapNotifications(notifications = []) {
  return notifications.map((notification) => ({
    id: notification.noti_id,
    title: notification.noti_title || '알림',
    message: notification.noti_msg || '',
    date: formatDate(notification.created_at),
    timeAgo: formatRelativeTime(notification.created_at),
    type: mapAlertType(notification.noti_type),
    isRead: Boolean(notification.is_received),
  }))
}

function mapAlertType(type) {
  switch (String(type || '').toUpperCase()) {
    case 'SUCCESS':
      return 'completed'
    case 'MISSED':
      return 'missed'
    default:
      return 'warning'
  }
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatRelativeTime(value) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  const diffMinutes = Math.max(
    0,
    Math.floor((Date.now() - date.getTime()) / 60000),
  )

  if (diffMinutes < 1) {
    return '방금 전'
  }

  if (diffMinutes < 60) {
    return `${diffMinutes}분 전`
  }

  const diffHours = Math.floor(diffMinutes / 60)

  if (diffHours < 24) {
    return `${diffHours}시간 전`
  }

  return `${Math.floor(diffHours / 24)}일 전`
}

export default AlertsPage
