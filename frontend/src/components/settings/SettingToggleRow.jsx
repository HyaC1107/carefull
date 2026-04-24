function SettingToggleRow({ title, description, checked, onChange }) {
  return (
    <div className="settings-row settings-row--toggle">
      <div className="settings-row__text">
        <p className="settings-row__title">{title}</p>
        <p className="settings-row__description">{description}</p>
      </div>

      <button
        type="button"
        className={`settings-toggle ${checked ? 'settings-toggle--active' : ''}`}
        onClick={onChange}
        aria-pressed={checked}
      >
        <span className="settings-toggle__thumb" />
      </button>
    </div>
  )
}

export default SettingToggleRow