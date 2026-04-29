import { useState } from 'react'

function GuardianEditModal({ initialData, onClose, onSave }) {
  const [form, setForm] = useState({
    guardian_name: initialData.guardian_name || '',
    guardian_phone: initialData.guardian_phone || '',
  })
  const [saving, setSaving] = useState(false)

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!form.guardian_name.trim() || !form.guardian_phone.trim()) {
      alert('필수 항목을 모두 입력해주세요.')
      return
    }

    setSaving(true)
    try {
      await onSave(form)
    } catch (err) {
      alert(err.message || '저장에 실패했습니다.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div
        className="settings-modal settings-modal--guardian"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="settings-modal__header">
          <div>
            <h3 className="settings-modal__title">보호자 정보 수정</h3>
            <p className="settings-modal__subtitle">보호자의 정보를 수정해주세요</p>
          </div>
          <button
            type="button"
            className="settings-modal__close-button"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <form className="settings-modal__body" onSubmit={handleSubmit}>
          <label className="settings-form-field">
            <span className="settings-form-field__label">보호자 이름 *</span>
            <input
              className="settings-form-field__input"
              value={form.guardian_name}
              onChange={(e) => handleChange('guardian_name', e.target.value)}
              placeholder="보호자 이름을 입력하세요"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">연락처 *</span>
            <input
              className="settings-form-field__input"
              value={form.guardian_phone}
              onChange={(e) => handleChange('guardian_phone', e.target.value)}
              placeholder="010-1234-5678"
            />
          </label>

          <div className="settings-modal__actions">
            <button
              type="button"
              className="settings-modal__button settings-modal__button--secondary"
              onClick={onClose}
              disabled={saving}
            >
              취소
            </button>
            <button
              type="submit"
              className="settings-modal__button settings-modal__button--primary"
              disabled={saving}
            >
              {saving ? '저장 중...' : '저장하기'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default GuardianEditModal
