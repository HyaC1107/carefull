function AlertListItem({ alert }) {
  return (
    <article
      className={`alert-list-item alert-list-item--${alert.type} ${
        alert.isRead ? 'alert-list-item--read' : ''
      }`}
    >
      <div className="alert-list-item__left">
        <div className={`alert-list-item__icon alert-list-item__icon--${alert.type}`} aria-hidden="true">
          {renderAlertIcon(alert.type)}
        </div>

        <div className="alert-list-item__content">
          <div className="alert-list-item__top-row">
            <h4 className="alert-list-item__title">{alert.title}</h4>
            <span className="alert-list-item__time">{alert.timeAgo}</span>
          </div>

          <p className="alert-list-item__message">{alert.message}</p>
          <p className="alert-list-item__date">{alert.date}</p>
        </div>
      </div>
    </article>
  )
}

function renderAlertIcon(type) {
  switch (type) {
    case 'missed':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M9 9l6 6M15 9l-6 6" />
        </svg>
      )

    case 'completed':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="m8 12 2.5 2.5L16 9" />
        </svg>
      )

    case 'warning':
      return (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v5" />
          <path d="M12 16h.01" />
        </svg>
      )

    default:
      return null
  }
}

export default AlertListItem