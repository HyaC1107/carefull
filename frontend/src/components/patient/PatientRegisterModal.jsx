import { useState } from 'react'

function PatientRegisterModal({ onClose, onSuccess }) {
  const [photoCaptured, setPhotoCaptured] = useState(false)
  const [form, setForm] = useState({
    name: '',
    birthDate: '',
    gender: '',
    bloodType: '',
    height: '',
    weight: '',
    phone: '',
    address: '',
    guardianName: '',
    guardianPhone: '',
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

    if (!form.name.trim() || !form.phone.trim()) {
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
          <div className="patient-photo-box">
            <p className="patient-form-field__label">환자 사진 등록 *</p>

            <div className="patient-photo-box__area">
              <div className="patient-photo-box__icon" aria-hidden="true">
                <svg
                  viewBox="0 0 24 24"
                  width="28"
                  height="28"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 7h3l2-2h6l2 2h3v11H4z" />
                  <circle cx="12" cy="13" r="4" />
                </svg>
              </div>

              <p className="patient-photo-box__description">
                버튼을 누르면 자동으로 5장의 사진이 촬영됩니다
              </p>

              <button
                type="button"
                className="patient-photo-box__button"
                onClick={() => setPhotoCaptured(true)}
              >
                사진 촬영 시작
              </button>
            </div>
          </div>

          <div className="patient-form-grid patient-form-grid--one">
            <label className="patient-form-field">
              <span className="patient-form-field__label">이름 *</span>
              <input
                className="patient-form-field__input"
                value={form.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="환자 이름을 입력하세요"
              />
            </label>
          </div>

          <div className="patient-form-grid patient-form-grid--two">
            <label className="patient-form-field">
              <span className="patient-form-field__label">생년월일</span>
              <input
                className="patient-form-field__input"
                value={form.birthDate}
                onChange={(e) => handleChange('birthDate', e.target.value)}
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
                value={form.bloodType}
                onChange={(e) => handleChange('bloodType', e.target.value)}
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
                value={form.guardianName}
                onChange={(e) => handleChange('guardianName', e.target.value)}
                placeholder="보호자 이름을 입력하세요"
              />
            </label>

            <label className="patient-form-field">
              <span className="patient-form-field__label">보호자 연락처</span>
              <input
                className="patient-form-field__input"
                value={form.guardianPhone}
                onChange={(e) => handleChange('guardianPhone', e.target.value)}
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