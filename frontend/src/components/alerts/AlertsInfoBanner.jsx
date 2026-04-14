function AlertsInfoBanner({ info }) {
  return (
    <section className="alerts-info-banner">
      <div className="alerts-info-banner__icon" aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          width="18"
          height="18"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
          <path d="M10 21a2 2 0 0 0 4 0" />
        </svg>
      </div>

      <div>
        <p className="alerts-info-banner__title">{info.title}</p>
        <p className="alerts-info-banner__description">{info.description}</p>
      </div>
    </section>
  )
}

export default AlertsInfoBanner