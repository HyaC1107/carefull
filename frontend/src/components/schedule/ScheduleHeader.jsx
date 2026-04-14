function ScheduleHeader() {
  return (
    <section className="schedule-header">
      <div>
        <h2 className="schedule-header__title">복약 일정 관리</h2>
        <p className="schedule-header__subtitle">
          환자의 일일 복약 스케줄을 관리합니다
        </p>
      </div>

      <button
        type="button"
        className="schedule-header__add-button"
        onClick={() => console.log('복약 일정 추가 기능은 나중에 연결 예정')}
      >
        + 복약 일정 추가
      </button>
    </section>
  )
}

export default ScheduleHeader