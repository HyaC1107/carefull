function SettingsInfoBanner({ title, description }) {
  return (
    <section className="settings-info-banner">
      <div className="settings-info-banner__icon" aria-hidden="true">
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
          <path d="M12 22s-7-4-7-10V6l7-3 7 3v6c0 6-7 10-7 10Z" />
        </svg>
      </div>

      <div>
        <p className="settings-info-banner__title">{title}</p>
        <p className="settings-info-banner__description">{description}</p>
      </div>
    </section>
  )
}

export default SettingsInfoBanner