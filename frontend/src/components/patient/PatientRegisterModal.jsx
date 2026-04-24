import { useState } from 'react'

function PatientRegisterModal({ onClose, onSuccess }) {
  const [photoCaptured, setPhotoCaptured] = useState(false)
  const [form, setForm] = useState({
    patient_name: '',
    birthdate: '',
    gender: '',
    bloodtype: '',
    height: '',
    weight: '',
    phone: '',
    address: '',
    guardian_name: '',
    guardian_phone: '',
  })

  const handleChange = (field, value) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!photoCaptured) {
      alert('환자 사진 등록을 먼저 완료해주세요.')
      return
    }

    if (!form.patient_name.trim() || !form.phone.trim()) {
      alert('이름과 연락처는 필수입니다.')
      return
    }

    onSuccess({
      ...form,
      photoCaptured: true,
    })
  }

  return (
    <div className="patient-modal-overlay" onClick={onClose}>
      <div
        className="patient-modal patient-modal--patient"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="patient-modal__header">
          <div>
            <h3 className="patient-modal__title">환자 등록</h3>
            <p className="patient-modal__subtitle">
              환자의 기본 정보와 사진을 등록하세요
            </p>
          </div>

          <button
            type="button"
            className="patient-modal__close-button"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <form className="patient-modal__body" onSubmit={handleSubmit}>
          

          <div className="patient-form-grid patient-form-grid--one">
            <label className="patient-form-field">
              <span className="patient-form-field__label">이름 *</span>
              <input
                className="patient-form-field__input"
                value={form.patient_name}
                onChange={(e) => handleChange('patient_name', e.target.value)}
                placeholder="환자 이름을 입력하세요"
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--two">
            <label className="patient-form-field">
              <span className="patient-form-field__label">생년월일</span>
              <input
                className="patient-form-field__input"
                value={form.birthdate}
                onChange={(e) => handleChange('birthdate', e.target.value)}
              />
            </label>

            <label className="patient-form-field">
              <span className="patient-form-field__label">성별 *</span>
              <input
                className="patient-form-field__input"
                value={form.gender}
                onChange={(e) => handleChange('gender', e.target.value)}
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--two">
            <label className="patient-form-field">
              <span className="patient-form-field__label">혈액형</span>
              <input
                className="patient-form-field__input"
                value={form.bloodtype}
                onChange={(e) => handleChange('bloodtype', e.target.value)}
              />
            </label>

            <label className="patient-form-field">
              <span className="patient-form-field__label">키 (cm)</span>
              <input
                className="patient-form-field__input"
                value={form.height}
                onChange={(e) => handleChange('height', e.target.value)}
                placeholder="예: 170"
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--one">
            <label className="patient-form-field">
              <span className="patient-form-field__label">몸무게 (kg)</span>
              <input
                className="patient-form-field__input"
                value={form.weight}
                onChange={(e) => handleChange('weight', e.target.value)}
                placeholder="예: 65"
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--one">
            <label className="patient-form-field">
              <span className="patient-form-field__label">연락처 *</span>
              <input
                className="patient-form-field__input"
                value={form.phone}
                onChange={(e) => handleChange('phone', e.target.value)}
                placeholder="010-1234-5678"
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--one">
            <label className="patient-form-field">
              <span className="patient-form-field__label">주소</span>
              <input
                className="patient-form-field__input"
                value={form.address}
                onChange={(e) => handleChange('address', e.target.value)}
                placeholder="주소를 입력하세요"
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--two">
            <label className="patient-form-field">
              <span className="patient-form-field__label">보호자 이름</span>
              <input
                className="patient-form-field__input"
                value={form.guardian_name}
                onChange={(e) => handleChange('guardian_name', e.target.value)}
                placeholder="보호자 이름을 입력하세요"
              />
            </label>

            <label className="patient-form-field">
              <span className="patient-form-field__label">보호자 연락처</span>
              <input
                className="patient-form-field__input"
                value={form.guardian_phone}
                onChange={(e) => handleChange('guardian_phone', e.target.value)}
                placeholder="010-1234-5678"
              />
            </label>
          </div>

          <div className="patient-form-message patient-form-message--warning">
            사진 등록을 완료해야 등록할 수 있습니다
          </div>

          <div className="patient-modal__actions">
            <button
              type="button"
              className="patient-modal__button patient-modal__button--secondary"
              onClick={onClose}
            >
              취소
            </button>

            <button
              type="submit"
              className="patient-modal__button patient-modal__button--primary"
            >
              등록하기
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default PatientRegisterModal
