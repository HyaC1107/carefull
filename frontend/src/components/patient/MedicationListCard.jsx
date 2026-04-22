import MedicationItem from './MedicationItem'

function MedicationListCard({ medications }) {
  return (
    <section className="patient-medication-card">
      <div className="patient-card-title-row">
        <div className="patient-card-title-row__icon" aria-hidden="true">
          <svg
            viewBox="0 0 24 24"
            width="16"
            height="16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10 13a4 4 0 0 1 0-6l1.2-1.2a4 4 0 0 1 5.6 5.6L15.5 12" />
            <path d="M14 11a4 4 0 0 1 0 6l-1.2 1.2a4 4 0 0 1-5.6-5.6L8.5 12" />
          </svg>
        </div>
        <h3 className="patient-card-title-row__title">
          복용 중인 약물 ({medications.length}개)
        </h3>
      </div>

      <div className="patient-medication-card__list">
        {medications.map((item) => (
          <MedicationItem key={item.id} medication={item} />
        ))}
      </div>
    </section>
  )
}

export default MedicationListCard