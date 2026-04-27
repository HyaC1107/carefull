import AlertListItem from './AlertListItem'

function AlertListCard({ alerts, totalCount, hasUnread, onMarkAllRead }) {
  return (
    <section className="alert-list-card">
      <div className="alert-list-card__header">
        <h3 className="alert-list-card__title">알림 목록 ({totalCount}건)</h3>

        <button
          type="button"
          className="alert-list-card__mark-read-button"
          onClick={onMarkAllRead}
          disabled={!hasUnread}
        >
          {hasUnread ? '모두 읽음 처리' : '✔'}
        </button>
      </div>

      <div className="alert-list-card__body">
        {alerts.length ? (
          alerts.map((alert) => <AlertListItem key={alert.id} alert={alert} />)
        ) : (
          <div className="alert-list-card__empty">
            <p className="alert-list-card__empty-title">표시할 알림이 없습니다.</p>
            <p className="alert-list-card__empty-subtitle">
              다른 필터를 선택하거나 새 알림을 기다려보세요.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}

export default AlertListCard
