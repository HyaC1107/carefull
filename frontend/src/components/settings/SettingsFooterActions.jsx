function SettingsFooterActions({ onCancel, onSave }) {
  return (
    <div className="settings-footer-actions">
      <button
        type="button"
        className="settings-footer-actions__button settings-footer-actions__button--secondary"
        onClick={onCancel}
      >
        취소
      </button>

      <button
        type="button"
        className="settings-footer-actions__button settings-footer-actions__button--primary"
        onClick={onSave}
      >
        저장하기
      </button>
    </div>
  )
}

export default SettingsFooterActions