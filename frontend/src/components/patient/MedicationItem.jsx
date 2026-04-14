function MedicationItem({ medication }) {
  return (
    <article className="patient-medication-item">
      <div className="patient-medication-item__left">
        <h4 className="patient-medication-item__name">{medication.name}</h4>
        <span className="patient-medication-item__ingredient">
          {medication.ingredient}
        </span>
        <p className="patient-medication-item__started-at">
          처방 시작: {medication.startedAt}
        </p>
      </div>

      <div className="patient-medication-item__right">
        <p className="patient-medication-item__dose">{medication.dose}</p>
        <p className="patient-medication-item__amount">{medication.amount}</p>
        <p className="patient-medication-item__timing">{medication.timing}</p>
      </div>
    </article>
  )
}

export default MedicationItem