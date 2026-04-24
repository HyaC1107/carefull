import DeviceStatusBox from './DeviceStatusBox'

function DeviceInfoCard({ statusList, detail }) {
  return (
    <section className="patient-device-card">
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
            <path d="M5 12a10 10 0 0 1 14 0" />
            <path d="M8.5 15.5a5 5 0 0 1 7 0" />
            <path d="M12 19h.01" />
          </svg>
        </div>
        <h3 className="patient-card-title-row__title">연결된 디바이스 정보</h3>
      </div>

      <div className="patient-device-card__status-grid">
        {statusList.map((item) => (
          <DeviceStatusBox key={item.id} item={item} />
        ))}
      </div>

      <div className="patient-device-card__detail-grid">
        <DeviceDetailItem label="모델명" value={detail.modelName} />
        <DeviceDetailItem label="시리얼 번호" value={detail.device_uid} />
        <DeviceDetailItem label="설치일" value={detail.registered_at} />
        <DeviceDetailItem label="펌웨어 버전" value={detail.firmwareVersion} />
      </div>
    </section>
  )
}

function DeviceDetailItem({ label, value }) {
  return (
    <div className="patient-device-card__detail-item">
      <p className="patient-device-card__detail-label">{label}</p>
      <p className="patient-device-card__detail-value">{value}</p>
    </div>
  )
}

export default DeviceInfoCard
