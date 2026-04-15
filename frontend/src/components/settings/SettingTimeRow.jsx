function SettingTimeRow({ title, description, value, onChange }) {
  return (
    <div className="settings-row settings-row--time">
      <div className="settings-row__text">
        <p className="settings-row__title">{title}</p>
        <p className="settings-row__description">{description}</p>
      </div>

      <div className="settings-time-box">
        <input
          type="time"
          className="settings-time-box__input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <span className="settings-time-box__icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </svg>
        </span>
      </div>
    </div>
  )
}

export default SettingTimeRow