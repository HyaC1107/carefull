// 이 컴포넌트는 알림 1개만 담당합니다.
// 알림 타입(missed/completed/warning)에 따라 색상을 다르게 보여줍니다.
function AlertItem({ alert }) {
  return (
    <div className={`alert-item alert-item--${alert.type}`}>
      <div className="alert-item__top">
        <div className="alert-item__left">
          <span className={`alert-item__badge alert-item__badge--${alert.type}`}>
            {alert.label}
          </span>
          <span className="alert-item__time">{alert.timeAgo}</span>
        </div>
      </div>

      <p className="alert-item__message">{alert.message}</p>
    </div>
  )
}

export default AlertItem