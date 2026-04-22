function SettingsSliderRow({ title, description, value, onChange }) {
  return (
    <div className="settings-row settings-row--slider">
      <div className="settings-row__top">
        <div className="settings-row__text">
          <p className="settings-row__title">{title}</p>
          <p className="settings-row__description">{description}</p>
        </div>

        <span className="settings-slider-row__value">{value}%</span>
      </div>

      <div className="settings-slider-row">
        <span className="settings-slider-row__icon" aria-hidden="true">
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
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M19 9a5 5 0 0 1 0 6" />
          </svg>
        </span>

        <input
          type="range"
          min="0"
          max="100"
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className="settings-slider-row__input"
        />
      </div>
    </div>
  )
}

export default SettingsSliderRow