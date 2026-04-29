import { useState } from 'react'

const GENDER_OPTIONS = [
  { value: 'M', label: '남성' },
  { value: 'F', label: '여성' },
]

const BLOODTYPE_OPTIONS = ['A', 'B', 'O', 'AB']

function PatientEditModal({ initialData, onClose, onSave }) {
  const [form, setForm] = useState({
    patient_name: initialData.patient_name || '',
    birthdate: initialData.birthdate
      ? String(initialData.birthdate).slice(0, 10)
      : '',
    gender: initialData.gender || 'M',
    phone: initialData.phone || '',
    address: initialData.address || '',
    bloodtype: initialData.bloodtype || 'A',
    height: initialData.height ?? '',
    weight: initialData.weight ?? '',
  })
  const [saving, setSaving] = useState(false)

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (
      !form.patient_name.trim() ||
      !form.birthdate ||
      !form.phone.trim() ||
      !form.address.trim()
    ) {
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
        className="settings-modal settings-modal--patient"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="settings-modal__header">
          <div>
            <h3 className="settings-modal__title">환자 정보 수정</h3>
            <p className="settings-modal__subtitle">환자의 기본 정보를 수정해주세요</p>
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
            <span className="settings-form-field__label">이름 *</span>
            <input
              className="settings-form-field__input"
              value={form.patient_name}
              onChange={(e) => handleChange('patient_name', e.target.value)}
              placeholder="환자 이름을 입력하세요"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">생년월일 *</span>
            <input
              type="date"
              className="settings-form-field__input"
              value={form.birthdate}
              onChange={(e) => handleChange('birthdate', e.target.value)}
            />
          </label>

          <div className="settings-form-row">
            <label className="settings-form-field">
              <span className="settings-form-field__label">성별</span>
              <select
                className="settings-form-field__input"
                value={form.gender}
                onChange={(e) => handleChange('gender', e.target.value)}
              >
                {GENDER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </label>

            <label className="settings-form-field">
              <span className="settings-form-field__label">혈액형</span>
              <select
                className="settings-form-field__input"
                value={form.bloodtype}
                onChange={(e) => handleChange('bloodtype', e.target.value)}
              >
                {BLOODTYPE_OPTIONS.map((bt) => (
                  <option key={bt} value={bt}>{bt}형</option>
                ))}
              </select>
            </label>
          </div>

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

          <div className="settings-form-row">
            <label className="settings-form-field">
              <span className="settings-form-field__label">키 (cm)</span>
              <input
                type="number"
                className="settings-form-field__input"
                value={form.height}
                onChange={(e) => handleChange('height', e.target.value)}
                placeholder="170"
                min="0"
              />
            </label>

            <label className="settings-form-field">
              <span className="settings-form-field__label">몸무게 (kg)</span>
              <input
                type="number"
                className="settings-form-field__input"
                value={form.weight}
                onChange={(e) => handleChange('weight', e.target.value)}
                placeholder="65"
                min="0"
              />
            </label>
          </div>

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

export default PatientEditModal
