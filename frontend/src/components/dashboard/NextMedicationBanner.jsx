// 이 컴포넌트는 맨 아래 "다음 복약 알림" 배너를 담당합니다.
function NextMedicationBanner({ nextMedication }) {
  return (
    <section className="next-medication-banner">
      <div className="next-medication-banner__icon" aria-hidden="true">
        🕒
      </div>

      <div>
        <p className="next-medication-banner__title">{nextMedication.title}</p>
        <p className="next-medication-banner__description">
          {nextMedication.description}
        </p>
      </div>
    </section>
  )
}

export default NextMedicationBanner