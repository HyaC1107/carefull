function SettingActionRow({ title, description, buttonLabel, onClick }) {
  return (
    <div className="settings-row settings-row--action">
      <div className="settings-row__text">
        <p className="settings-row__title">{title}</p>
        <p className="settings-row__description">{description}</p>
      </div>

      <button
        type="button"
        className="settings-action-button"
        onClick={onClick}
      >
        {buttonLabel}
      </button>
    </div>
  )
}

export default SettingActionRow