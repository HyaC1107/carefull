import { useEffect, useRef, useState } from 'react'
import { requestJson } from '../../api'

function ScheduleAddModal({ selectedDateLabel, onClose, onSubmit }) {
  const [repeatType, setRepeatType] = useState('none')
  const [form, setForm] = useState({
    dose: '1',
    time_to_take: '',
    start_date: '',
    end_date: '',
  })

  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedMed, setSelectedMed] = useState(null)

  const debounceRef = useRef(null)

  useEffect(() => {
    const query = searchQuery.trim()

    if (!query) {
      setSearchResults([])
      setShowDropdown(false)
      return
    }

    if (selectedMed && searchQuery === selectedMed.medi_name) {
      return
    }

    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setIsSearching(true)
      try {
        const data = await requestJson(
          `/api/medication/search?keyword=${encodeURIComponent(query)}`,
        )
        setSearchResults(data?.data || [])
        setShowDropdown(true)
      } catch {
        setSearchResults([])
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(debounceRef.current)
  }, [searchQuery])

  const handleSearchChange = (e) => {
    const value = e.target.value
    setSearchQuery(value)
    if (selectedMed && value !== selectedMed.medi_name) {
      setSelectedMed(null)
    }
  }

  const handleSelectMed = (med) => {
    setSelectedMed(med)
    setSearchQuery(med.medi_name)
    setShowDropdown(false)
    setSearchResults([])
  }

  const handleSearchBlur = () => {
    setTimeout(() => setShowDropdown(false), 150)
  }

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (event) => {
    event.preventDefault()

    if (!selectedMed) {
      alert('약을 목록에서 선택해주세요.')
      return
    }

    if (!form.dose.trim() || !form.time_to_take.trim()) {
      alert('수량과 복용 시간은 필수입니다.')
      return
    }

    onSubmit({
      ...form,
      medi_id: selectedMed.medi_id,
      medi_name: selectedMed.medi_name,
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
              value={form.time_to_take}
              onChange={(e) => handleChange('time_to_take', e.target.value)}
            />
          </section>

          <section className="schedule-modal__section schedule-modal__section--highlight">
            <div className="schedule-modal__section-title-row">
              <span
                className="schedule-modal__section-icon schedule-modal__section-icon--pill"
                aria-hidden="true"
              >
                💊
              </span>
              <h4 className="schedule-modal__section-title">약 정보</h4>
            </div>

            <label className="schedule-modal__field">
              <span className="schedule-modal__label">약 이름 *</span>
              <div className="schedule-modal__search-wrapper">
                <input
                  className="schedule-modal__input"
                  value={searchQuery}
                  onChange={handleSearchChange}
                  onBlur={handleSearchBlur}
                  onFocus={() => {
                    if (searchResults.length > 0) setShowDropdown(true)
                  }}
                  placeholder="약 이름을 입력하세요 (예: 졸피뎀)"
                  autoComplete="off"
                />

                {showDropdown && (
                  <div className="schedule-modal__search-dropdown">
                    {isSearching ? (
                      <p className="schedule-modal__search-empty">검색 중...</p>
                    ) : searchResults.length > 0 ? (
                      searchResults.map((med) => (
                        <div
                          key={med.medi_id}
                          className="schedule-modal__search-item"
                          onMouseDown={() => handleSelectMed(med)}
                        >
                          {med.medi_name}
                        </div>
                      ))
                    ) : (
                      <p className="schedule-modal__search-empty">
                        검색 결과가 없습니다
                      </p>
                    )}
                  </div>
                )}
              </div>
              {selectedMed ? (
                <span className="schedule-modal__search-hint">
                  ✓ {selectedMed.medi_name} 선택됨
                </span>
              ) : searchQuery.trim() && !isSearching ? (
                <span className="schedule-modal__search-hint">
                  목록에서 약을 선택해주세요
                </span>
              ) : null}
            </label>

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
                  value={form.start_date}
                  onChange={(e) => handleChange('start_date', e.target.value)}
                />
              </label>

              <label className="schedule-modal__field">
                <span className="schedule-modal__label">종료일 (선택)</span>
                <input
                  type="date"
                  className="schedule-modal__input"
                  value={form.end_date}
                  onChange={(e) => handleChange('end_date', e.target.value)}
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
