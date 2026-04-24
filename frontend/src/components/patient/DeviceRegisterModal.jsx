import { useState } from 'react'

function DeviceRegisterModal({ onClose, onSuccess }) {
  const [device_uid, setDeviceUid] = useState('')
  const [deviceName, setDeviceName] = useState('')

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!device_uid.trim() || !deviceName.trim()) {
      alert('시리얼 번호와 기기 이름을 입력해주세요.')
      return
    }

    onSuccess({
      device_uid,
      deviceName,
    })
  }

  return (
    <div className="patient-modal-overlay" onClick={onClose}>
      <div
        className="patient-modal patient-modal--device"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="patient-modal__header">
          <div>
            <h3 className="patient-modal__title">기기 등록</h3>
            <p className="patient-modal__subtitle">
              복약 모니터링 기기 정보를 입력해주세요
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
          <label className="patient-form-field">
            <span className="patient-form-field__label">시리얼 번호 *</span>
            <input
              className="patient-form-field__input"
              value={device_uid}
              onChange={(event) => setDeviceUid(event.target.value)}
              placeholder="예: SM-2024-A1234"
            />
            <span className="patient-form-field__hint">
              기기 뒷면 또는 사용자 메뉴에서 확인할 수 있습니다
            </span>
          </label>

          <label className="patient-form-field">
            <span className="patient-form-field__label">기기 이름 *</span>
            <input
              className="patient-form-field__input"
              value={deviceName}
              onChange={(event) => setDeviceName(event.target.value)}
              placeholder="예: 거실 복약 모니터"
            />
            <span className="patient-form-field__hint">
              쉽게 식별할 수 있는 기기명을 입력하세요
            </span>
          </label>

          <div className="patient-form-message patient-form-message--success">
            시리얼 번호는 기기 옆면 또는 사용자 메뉴에서 확인할 수 있습니다.
            등록 후 기기가 자동으로 페어링됩니다.
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

export default DeviceRegisterModal
