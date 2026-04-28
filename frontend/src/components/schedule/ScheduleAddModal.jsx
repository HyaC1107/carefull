import { useState } from 'react'

function ScheduleAddModal({ selectedDateLabel, onClose, onSubmit }) {
  const [repeatType, setRepeatType] = useState('none')
  const [form, setForm] = useState({
    medicationName: '',
    dose: '1',
    time: '',
    startDate: '',
    endDate: '',
  })

  const handleChange = (field, value) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!form.medicationName.trim() || !form.dose.trim() || !form.time.trim()) {
      alert('약 이름, 수량, 복용 시간은 필수입니다.')
      return
    }

    onSubmit({
      ...form,
      repeatType,
    })
  }

  return (
    <div className="schedule-modal-overlay" onClick={onClose}>
      <div
        className="schedule-modal schedule-modal--figma"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="schedule-modal__header">
          <div>
            <h3 className="schedule-modal__title">복약 일정 추가</h3>
            <p className="schedule-modal__subtitle">
              환자의 복약 스케줄을 관리합니다
            </p>
          </div>

          <button
            type="button"
            className="schedule-modal__close-button"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <form className="schedule-modal__body" onSubmit={handleSubmit}>
          <div className="schedule-modal__date-chip">
            <span className="schedule-modal__date-chip-icon" aria-hidden="true">
              📅
            </span>
            <span>{selectedDateLabel}</span>
          </div>

          <section className="schedule-modal__section">
            <div className="schedule-modal__section-title-row">
              <span className="schedule-modal__section-icon" aria-hidden="true">
                🕒
              </span>
              <h4 className="schedule-modal__section-title">복용 시간</h4>
            </div>

            <input
              type="time"
              className="schedule-modal__input"
              value={form.time}
              onChange={(e) => handleChange('time', e.target.value)}
            />
          </section>

          <section className="schedule-modal__section schedule-modal__section--highlight">
            <div className="schedule-modal__section-header">
              <div className="schedule-modal__section-title-row">
                <span
                  className="schedule-modal__section-icon schedule-modal__section-icon--pill"
                  aria-hidden="true"
                >
                  💊
                </span>
                <h4 className="schedule-modal__section-title">약 정보</h4>
              </div>

              <button
                type="button"
                className="schedule-modal__mini-button"
                onClick={() => alert('약 추가 기능은 나중에 연결 예정')}
              >
                + 약 추가
              </button>
            </div>

            <label className="schedule-modal__field">
              <span className="schedule-modal__label">약 이름 *</span>
              <input
                className="schedule-modal__input"
                value={form.medicationName}
                onChange={(e) => handleChange('medicationName', e.target.value)}
                placeholder="약 이름을 검색하세요..."
              />
            </label>

            <label className="schedule-modal__field">
              <span className="schedule-modal__label">수량 (정/캡) *</span>
              <input
                className="schedule-modal__input"
                value={form.dose}
                onChange={(e) => handleChange('dose', e.target.value)}
              />
            </label>

            <div className="schedule-modal__hint-box">
              💡 약 이름을 입력하면 자동으로 목록에 표시됩니다
            </div>
          </section>

          <section className="schedule-modal__section">
            <div className="schedule-modal__section-title-row">
              <span className="schedule-modal__section-icon" aria-hidden="true">
                📅
              </span>
              <h4 className="schedule-modal__section-title">복용 기간</h4>
            </div>

            <div className="schedule-modal__grid schedule-modal__grid--two">
              <label className="schedule-modal__field">
                <span className="schedule-modal__label">시작일 *</span>
                <input
                  type="date"
                  className="schedule-modal__input"
                  value={form.startDate}
                  onChange={(e) => handleChange('startDate', e.target.value)}
                />
              </label>

              <label className="schedule-modal__field">
                <span className="schedule-modal__label">종료일 (선택)</span>
                <input
                  type="date"
                  className="schedule-modal__input"
                  value={form.endDate}
                  onChange={(e) => handleChange('endDate', e.target.value)}
                />
              </label>
            </div>
          </section>

          <section className="schedule-modal__section">
            <div className="schedule-modal__section-title-row">
              <span className="schedule-modal__section-icon" aria-hidden="true">
                Ⓡ
              </span>
              <h4 className="schedule-modal__section-title">반복 주기 (선택)</h4>
            </div>

            <div className="schedule-modal__repeat-buttons">
              <button
                type="button"
                className={`schedule-modal__repeat-button ${
                  repeatType === 'none'
                    ? 'schedule-modal__repeat-button--active'
                    : ''
                }`}
                onClick={() => setRepeatType('none')}
              >
                반복 안 함
              </button>

              <button
                type="button"
                className={`schedule-modal__repeat-button ${
                  repeatType === 'weekly'
                    ? 'schedule-modal__repeat-button--active'
                    : ''
                }`}
                onClick={() => setRepeatType('weekly')}
              >
                요일 선택
              </button>

              <button
                type="button"
                className={`schedule-modal__repeat-button ${
                  repeatType === 'interval'
                    ? 'schedule-modal__repeat-button--active'
                    : ''
                }`}
                onClick={() => setRepeatType('interval')}
              >
                일수 간격
              </button>
            </div>

            <div className="schedule-modal__repeat-hint">
              1회성 복약으로 설정됩니다.
            </div>
          </section>

          <div className="schedule-modal__notice">
            ✅ 복약 시간 10분 전에 알림이 자동으로 발송됩니다. 환자가 복약을 완료하면
            기기에서 자동으로 기록됩니다.
          </div>

          <div className="schedule-modal__actions">
            <button
              type="button"
              className="schedule-modal__button schedule-modal__button--secondary"
              onClick={onClose}
            >
              취소
            </button>

            <button
              type="submit"
              className="schedule-modal__button schedule-modal__button--primary"
            >
              추가
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ScheduleAddModal