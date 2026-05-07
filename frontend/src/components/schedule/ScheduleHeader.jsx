function ScheduleHeader({ onOpenAddModal, onOpenDeleteModal }) {
  return (
    <section className="schedule-header">
      <div>
        <h2 className="schedule-header__title">복약 일정 관리</h2>
        <p className="schedule-header__subtitle">
          환자의 일일 복약 스케줄을 관리합니다
        </p>
      </div>

      <div className="schedule-header__actions">
        <button
          type="button"
          className="schedule-header__add-button"
          onClick={onOpenAddModal}
        >
          + 복약 일정 추가
        </button>
        <button
          type="button"
          className="schedule-header__delete-button"
          onClick={onOpenDeleteModal}
        >
          복약 일정 삭제
        </button>
      </div>
    </section>
  )
}

export default ScheduleHeader
