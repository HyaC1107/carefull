// 이 컴포넌트는 "스마트 복약 디바이스" 영역 전체를 담당합니다.
// 디바이스 연결 상태, 약 잔량, 마지막 동기화 시간, 다음 복약 시간을 보여줍니다.
function DeviceStatusSection({ deviceStatus }) {
  return (
    <section className="dashboard-section dashboard-device">
      <h2 className="dashboard-section__title">스마트 복약 디바이스</h2>

      <div className="dashboard-device__cards">
        {/* 연결 상태 카드 */}
        <div className="dashboard-device__status-card dashboard-device__status-card--green">
          <div className="dashboard-device__status-icon" aria-hidden="true">
            {/* 와이파이/연결 상태 아이콘 */}
            <svg
              viewBox="0 0 24 24"
              width="38"
              height="38"
              fill="none"
              stroke="#16a34a"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 9a11 11 0 0 1 14 0" />
              <path d="M8 12a7 7 0 0 1 8 0" />
              <path d="M11 15a3 3 0 0 1 2 0" />
              <circle cx="12" cy="18" r="1" fill="#16a34a" stroke="none" />
            </svg>
          </div>
          <p className="dashboard-device__label">연결 상태</p>
          <p className="dashboard-device__value dashboard-device__value--green">
            {deviceStatus.connectionStatus}
          </p>
        </div>

        {/* 약 잔량 카드 */}
        <div className="dashboard-device__status-card dashboard-device__status-card--blue">
          <div className="dashboard-device__status-icon" aria-hidden="true">
            {/* 물방울 아이콘 */}
            <svg
              viewBox="0 0 24 24"
              width="38"
              height="38"
              fill="#2563eb"
            >
              <path d="M12 2c-.7 1.2-5.5 7-5.5 11.1A5.5 5.5 0 0 0 12 18.6a5.5 5.5 0 0 0 5.5-5.5C17.5 9 12.7 3.2 12 2Z" />
            </svg>
          </div>
          <p className="dashboard-device__label">약 잔량</p>
          <p className="dashboard-device__value dashboard-device__value--blue">
            {deviceStatus.medicineLeftPercent}
          </p>
        </div>
      </div>

      <div className="dashboard-device__meta">
        <div>
          <p className="dashboard-device__meta-label">마지막 동기화</p>
          <p className="dashboard-device__meta-value">{deviceStatus.lastSynced}</p>
        </div>

        <div>
          <p className="dashboard-device__meta-label">다음 복약 시간</p>
          <p className="dashboard-device__meta-value">{deviceStatus.nextDoseTime}</p>
        </div>
      </div>
    </section>
  )
}

export default DeviceStatusSection