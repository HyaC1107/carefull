function PatientProfileCard({ profile }) {
  return (
    <section className="patient-profile-card">
      <div className="patient-profile-card__header">
        <div className="patient-profile-card__avatar" aria-hidden="true">
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

        <div>
          <h3 className="patient-profile-card__name">{profile.name}</h3>
          <p className="patient-profile-card__summary">{profile.ageGenderBlood}</p>
        </div>
      </div>

      <div className="patient-profile-card__grid">
        <InfoItem
          icon={renderPhoneIcon()}
          label="연락처"
          value={profile.phone}
        />
        <InfoItem
          icon={renderGuardianIcon()}
          label="보호자"
          value={profile.guardianName}
        />
        <InfoItem
          icon={renderLocationIcon()}
          label="주소"
          value={profile.address}
        />
        <InfoItem
          icon={renderPhoneIcon()}
          label="보호자 연락처"
          value={profile.guardianPhone}
        />
        <InfoItem
          icon={renderCalendarIcon()}
          label="서비스 등록일"
          value={profile.registeredAt}
        />
        <InfoItem
          icon={renderPulseIcon()}
          label="신체 정보"
          value={profile.physicalInfo}
        />
      </div>
    </section>
  )
}

function InfoItem({ icon, label, value }) {
  return (
    <div className="patient-profile-card__info-item">
      <div className="patient-profile-card__info-icon" aria-hidden="true">
        {icon}
      </div>
      <div>
        <p className="patient-profile-card__info-label">{label}</p>
        <p className="patient-profile-card__info-value">{value}</p>
      </div>
    </div>
  )
}

function renderPhoneIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.9.33 1.78.63 2.62a2 2 0 0 1-.45 2.11L8 9.91a16 16 0 0 0 6.09 6.09l1.46-1.29a2 2 0 0 1 2.11-.45c.84.3 1.72.51 2.62.63A2 2 0 0 1 22 16.92z" />
    </svg>
  )
}

function renderGuardianIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c1.5-4 5-6 8-6s6.5 2 8 6" />
    </svg>
  )
}

function renderLocationIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 21s-6-5.33-6-11a6 6 0 1 1 12 0c0 5.67-6 11-6 11Z" />
      <circle cx="12" cy="10" r="2" />
    </svg>
  )
}

function renderCalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M8 3v4M16 3v4M4 9h16" />
    </svg>
  )
}

function renderPulseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 12h-4l-3 6-4-12-3 6H2" />
    </svg>
  )
}

export default PatientProfileCard