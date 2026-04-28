function PatientEmptyState({
  hasDevice,
  onOpenDeviceModal,
  onOpenPatientModal,
}) {
  return (
    <section className="patient-empty-state">
      <div className="patient-page-header">
        <h2 className="patient-page-header__title">시스템 등록</h2>
        <p className="patient-page-header__subtitle">
          복약 모니터링을 시작하기 위해 기기와 환자 정보를 등록해주세요
        </p>
      </div>

      <div className="patient-empty-state__cards">
        <article className="patient-register-card">
          <div className="patient-register-card__icon patient-register-card__icon--device" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              width="26"
              height="26"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s-7-4-7-10V6l7-3 7 3v6c0 6-7 10-7 10Z" />
            </svg>
          </div>

          <div className="patient-register-card__content">
            <h3 className="patient-register-card__title">기기 등록</h3>
            <p className="patient-register-card__subtitle">복약 모니터링 기기</p>
            <p className="patient-register-card__description">
              스마트 복약 기기의 시리얼 번호와 이름을 등록하여 환자의 복약 현황을
              실시간으로 모니터링하세요.
            </p>
          </div>

          <button
            type="button"
            className="patient-register-card__button"
            onClick={onOpenDeviceModal}
          >
            기기 등록하기
          </button>
        </article>

        <article
          className={`patient-register-card ${
            !hasDevice ? 'patient-register-card--disabled' : ''
          }`}
        >
          <div className="patient-register-card__icon patient-register-card__icon--patient" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              width="26"
              height="26"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="8" r="4" />
              <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
            </svg>
          </div>

          <div className="patient-register-card__content">
            <h3 className="patient-register-card__title">환자 등록</h3>
            <p className="patient-register-card__subtitle">환자 정보 및 사진</p>
            <p className="patient-register-card__description">
              환자의 기본 정보와 얼굴 사진을 등록하여 복약 모니터링을 시작하세요.
              사진은 자동으로 촬영됩니다.
            </p>

            {!hasDevice ? (
              <p className="patient-register-card__notice">
                먼저 기기를 등록해야 환자 등록을 진행할 수 있습니다.
              </p>
            ) : null}
          </div>

          <button
            type="button"
            className="patient-register-card__button"
            onClick={onOpenPatientModal}
            disabled={!hasDevice}
          >
            환자 등록하기
          </button>
        </article>
      </div>
    </section>
  )
}

export default PatientEmptyState