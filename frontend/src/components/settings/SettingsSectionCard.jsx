function SettingsSectionCard({ title, children }) {
  return (
    <section className="settings-section-card">
      <h3 className="settings-section-card__title">{title}</h3>
      <div className="settings-section-card__divider" />
      <div className="settings-section-card__body">{children}</div>
    </section>
  )
}

export default SettingsSectionCard