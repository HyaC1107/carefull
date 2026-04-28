import { useEffect, useState } from 'react'

function GuardianEditModal({ initialData, onClose, onSave }) {
  const [form, setForm] = useState(initialData)

  useEffect(() => {
    setForm(initialData)
  }, [initialData])

  const handleChange = (field, value) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (
      !form.name.trim() ||
      !form.phone.trim() ||
      !form.address.trim() ||
      !form.relation.trim() ||
      !form.email.trim()
    ) {
      alert('필수 항목을 모두 입력해주세요.')
      return
    }

    onSave(form)
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
            <p className="settings-modal__subtitle">
              보호자의 정보를 수정해주세요
            </p>
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
              value={form.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="보호자 이름을 입력하세요"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">연락처 *</span>
            <input
              className="settings-form-field__input"
              value={form.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
              placeholder="010-1234-5678"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">주소 *</span>
            <input
              className="settings-form-field__input"
              value={form.address}
              onChange={(e) => handleChange('address', e.target.value)}
              placeholder="주소를 입력하세요"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">관계 *</span>
            <input
              className="settings-form-field__input"
              value={form.relation}
              onChange={(e) => handleChange('relation', e.target.value)}
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">이메일 *</span>
            <input
              className="settings-form-field__input"
              value={form.email}
              onChange={(e) => handleChange('email', e.target.value)}
              placeholder="example@email.com"
            />
          </label>

          <div className="settings-modal__actions">
            <button
              type="button"
              className="settings-modal__button settings-modal__button--secondary"
              onClick={onClose}
            >
              취소
            </button>

            <button
              type="submit"
              className="settings-modal__button settings-modal__button--primary"
            >
              저장하기
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default GuardianEditModal