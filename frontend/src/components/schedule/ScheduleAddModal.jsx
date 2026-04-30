import { useEffect, useRef, useState } from 'react'
import { requestJson } from '../../api'

const DOSE_INTERVAL_OPTIONS = [1, 2, 3, 4, 5]

function ScheduleAddModal({
  selectedDateLabel,
  onClose,
  onSubmit,
  onPreviewPrescription,
  onConfirmPrescription,
}) {
  const [repeatType, setRepeatType] = useState('none')
  const [doseInterval, setDoseInterval] = useState('')
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
  const [selectedMeds, setSelectedMeds] = useState([])
  const [selectedTimes, setSelectedTimes] = useState([])
  const [prescriptionFile, setPrescriptionFile] = useState(null)
  const [prescriptionMedications, setPrescriptionMedications] = useState([])
  const [prescriptionWarnings, setPrescriptionWarnings] = useState([])
  const [isPrescriptionAnalyzing, setIsPrescriptionAnalyzing] = useState(false)
  const [isPrescriptionConfirming, setIsPrescriptionConfirming] = useState(false)

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
    setSelectedMeds((prev) =>
      prev.some((item) => item.medi_id === med.medi_id) ? prev : [...prev, med],
    )
    setSearchQuery('')
    setShowDropdown(false)
    setSearchResults([])
  }

  const handleSearchBlur = () => {
    setTimeout(() => setShowDropdown(false), 150)
  }

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  const handleAddTime = () => {
    const nextTime = form.time_to_take.trim()

    if (!nextTime) {
      alert('복용 시간을 입력해주세요.')
      return
    }

    setSelectedTimes((prev) =>
      prev.includes(nextTime) ? prev : [...prev, nextTime].sort(),
    )
    handleChange('time_to_take', '')
  }

  const handleRemoveTime = (timeToRemove) => {
    setSelectedTimes((prev) => prev.filter((time) => time !== timeToRemove))
  }

  const handleSubmit = (event) => {
    event.preventDefault()
    const timeToTakeList =
      selectedTimes.length > 0
        ? selectedTimes
        : form.time_to_take.trim()
          ? [form.time_to_take.trim()]
          : []

    if (selectedMeds.length === 0) {
      alert('약을 목록에서 선택해주세요.')
      return
    }

    if (!form.dose.trim() || timeToTakeList.length === 0) {
      alert('수량과 복용 시간은 필수입니다.')
      return
    }

    onSubmit({
      ...form,
      time_to_take: timeToTakeList[0],
      time_to_take_list: timeToTakeList,
      medi_id: selectedMeds[0].medi_id,
      medi_name: selectedMeds.map((med) => med.medi_name).join(', '),
      medications: selectedMeds.map((med) => ({
        medi_id: med.medi_id,
        medi_name: med.medi_name,
      })),
      dose_interval:
        repeatType === 'interval' && doseInterval ? Number(doseInterval) : null,
      repeatType,
    })
  }

  const handlePrescriptionPreview = async () => {
    if (!prescriptionFile || !onPreviewPrescription) {
      return
    }

    setIsPrescriptionAnalyzing(true)
    try {
      const data = await onPreviewPrescription(prescriptionFile)
      setPrescriptionMedications(
        Array.isArray(data?.medications) ? data.medications : [],
      )
      setPrescriptionWarnings(Array.isArray(data?.warnings) ? data.warnings : [])
    } catch (error) {
      console.error('prescription preview error:', error)
      alert(error.message || '처방전 분석에 실패했습니다.')
    } finally {
      setIsPrescriptionAnalyzing(false)
    }
  }

  const handlePrescriptionMedicationChange = (index, field, value) => {
    setPrescriptionMedications((prev) =>
      prev.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    )
  }

  const handlePrescriptionConfirm = async () => {
    if (!onConfirmPrescription) {
      return
    }

    setIsPrescriptionConfirming(true)
    try {
      await onConfirmPrescription({
        medications: prescriptionMedications.map((item) => ({
          ...item,
          times: parseTimesInput(item.times),
        })),
      })
      alert('처방전 복약 일정이 등록되었습니다.')
    } catch (error) {
      console.error('prescription confirm error:', error)
      alert(error.message || '처방전 복약 일정 등록에 실패했습니다.')
    } finally {
      setIsPrescriptionConfirming(false)
    }
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
            <div className="schedule-modal__section-header">
              <div className="schedule-modal__section-title-row">
                <span className="schedule-modal__section-icon" aria-hidden="true">
                  ?뱟
                </span>
                <h4 className="schedule-modal__section-title">처방전 이미지</h4>
              </div>
              <button
                type="button"
                className="schedule-modal__mini-button"
                onClick={handlePrescriptionPreview}
                disabled={!prescriptionFile || isPrescriptionAnalyzing}
              >
                {isPrescriptionAnalyzing ? '분석 중' : '분석'}
              </button>
            </div>

            <input
              type="file"
              accept="image/*"
              className="schedule-modal__input"
              onChange={(event) => {
                setPrescriptionFile(event.target.files?.[0] || null)
                setPrescriptionMedications([])
                setPrescriptionWarnings([])
              }}
            />

            {prescriptionWarnings.length > 0 ? (
              <div className="schedule-modal__repeat-hint">
                {prescriptionWarnings.join(' / ')}
              </div>
            ) : null}

            {prescriptionMedications.length > 0 ? (
              <div className="schedule-modal__selected-meds">
                {prescriptionMedications.map((item, index) => (
                  <div key={`${item.medicine_name}-${index}`} className="schedule-modal__field">
                    <input
                      className="schedule-modal__input"
                      value={item.medicine_name || ''}
                      onChange={(event) =>
                        handlePrescriptionMedicationChange(
                          index,
                          'medicine_name',
                          event.target.value,
                        )
                      }
                      placeholder="약 이름"
                    />
                    <input
                      className="schedule-modal__input"
                      value={formatTimesInput(item.times)}
                      onChange={(event) =>
                        handlePrescriptionMedicationChange(
                          index,
                          'times',
                          event.target.value,
                        )
                      }
                      placeholder="08:00, 13:00, 19:00"
                    />
                    <input
                      type="date"
                      className="schedule-modal__input"
                      value={item.start_date || ''}
                      onChange={(event) =>
                        handlePrescriptionMedicationChange(
                          index,
                          'start_date',
                          event.target.value,
                        )
                      }
                    />
                    <input
                      type="date"
                      className="schedule-modal__input"
                      value={item.end_date || ''}
                      onChange={(event) =>
                        handlePrescriptionMedicationChange(
                          index,
                          'end_date',
                          event.target.value,
                        )
                      }
                    />
                    <input
                      className="schedule-modal__input"
                      value={item.memo || ''}
                      onChange={(event) =>
                        handlePrescriptionMedicationChange(index, 'memo', event.target.value)
                      }
                      placeholder="메모"
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className="schedule-modal__button schedule-modal__button--primary"
                  onClick={handlePrescriptionConfirm}
                  disabled={isPrescriptionConfirming}
                >
                  {isPrescriptionConfirming ? '등록 중' : '최종 확인'}
                </button>
              </div>
            ) : null}
          </section>

          <section className="schedule-modal__section">
            <div className="schedule-modal__section-header">
              <div className="schedule-modal__section-title-row">
                <span className="schedule-modal__section-icon" aria-hidden="true">
                  🕒
                </span>
                <h4 className="schedule-modal__section-title">복용 시간</h4>
              </div>
              <button
                type="button"
                className="schedule-modal__mini-button"
                onClick={handleAddTime}
              >
                추가
              </button>
            </div>

            <input
              type="time"
              className="schedule-modal__input"
              value={form.time_to_take}
              onChange={(e) => handleChange('time_to_take', e.target.value)}
            />
            {selectedTimes.length > 0 ? (
              <div className="schedule-modal__selected-meds">
                {selectedTimes.map((time) => (
                  <span key={time} className="schedule-modal__selected-med">
                    {time}
                    <button
                      type="button"
                      className="schedule-modal__selected-med-remove"
                      onClick={() => handleRemoveTime(time)}
                      aria-label={`${time} 삭제`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            ) : null}
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
              {selectedMeds.length > 0 ? (
                <div className="schedule-modal__selected-meds">
                  {selectedMeds.map((med) => (
                    <span
                      key={med.medi_id}
                      className="schedule-modal__selected-med"
                    >
                      {med.medi_name}
                    </span>
                  ))}
                </div>
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
                onClick={() => {
                  setRepeatType('none')
                  setDoseInterval('')
                }}
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
                disabled
                hidden
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
                onClick={() => {
                  setRepeatType('interval')
                  setDoseInterval((prev) => prev || '1')
                }}
              >
                일수 간격
              </button>
            </div>

            {repeatType === 'interval' ? (
              <div className="schedule-modal__repeat-buttons">
                {DOSE_INTERVAL_OPTIONS.map((interval) => (
                  <button
                    key={interval}
                    type="button"
                    className={`schedule-modal__repeat-button ${
                      Number(doseInterval) === interval
                        ? 'schedule-modal__repeat-button--active'
                        : ''
                    }`}
                    onClick={() => setDoseInterval(String(interval))}
                  >
                    {interval}일 간격
                  </button>
                ))}
              </div>
            ) : null}

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

function formatTimesInput(times) {
  return Array.isArray(times) ? times.join(', ') : String(times || '')
}

function parseTimesInput(value) {
  if (Array.isArray(value)) {
    return value
  }

  return String(value || '')
    .split(',')
    .map((time) => time.trim())
    .filter(Boolean)
}

export default ScheduleAddModal
