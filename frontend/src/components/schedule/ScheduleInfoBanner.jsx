// 페이지 하단 안내 배너
function ScheduleInfoBanner({ info }) {
  return (
    <section className="schedule-info-banner">
      <div className="schedule-info-banner__icon" aria-hidden="true">
        🔗
      </div>

      <div>
        <p className="schedule-info-banner__title">{info.title}</p>
        <p className="schedule-info-banner__description">{info.description}</p>
      </div>
    </section>
  )
}

export default ScheduleInfoBanner