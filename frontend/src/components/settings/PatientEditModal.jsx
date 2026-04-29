import { useEffect, useState } from 'react'
import { patientProfile } from '../../data/patientMock'

function PatientEditModal({ onClose, onSave }) {
  const [form, setForm] = useState(patientProfile)

  const handleChange = (field, value) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!form.name.trim() || !form.phone.trim()) {
      alert('이름과 연락처는 필수 항목입니다.')
      return
    }

    onSave(form)
  }

  return (
    <div className="settings-modal-overlay" onClick={onClose}>
      <div
        className="settings-modal settings-modal--patient"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="settings-modal__header">
          <div>
            <h3 className="settings-modal__title">환자 정보 수정</h3>
            <p className="settings-modal__subtitle">
              환자의 정보를 수정해주세요
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
            <span className="settings-form-field__label">이름 *</span>
            <input
              className="settings-form-field__input"
              value={form.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="환자 이름을 입력하세요"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">상세 정보 (나이/성별/혈액형)</span>
            <input
              className="settings-form-field__input"
              value={form.ageGenderBlood}
              onChange={(e) => handleChange('ageGenderBlood', e.target.value)}
              placeholder="예: 76세 · 여성 · 혈액형 A형"
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
            <span className="settings-form-field__label">주소</span>
            <input
              className="settings-form-field__input"
              value={form.address}
              onChange={(e) => handleChange('address', e.target.value)}
              placeholder="주소를 입력하세요"
            />
          </label>

          <label className="settings-form-field">
            <span className="settings-form-field__label">신체 정보 (키/몸무게)</span>
            <input
              className="settings-form-field__input"
              value={form.physicalInfo}
              onChange={(e) => handleChange('physicalInfo', e.target.value)}
              placeholder="예: 키 158cm · 체중 62kg"
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

export default PatientEditModal
