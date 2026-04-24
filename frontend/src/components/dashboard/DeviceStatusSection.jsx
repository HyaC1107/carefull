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
            {deviceStatus.connection_status}
          </p>
        </div>

        {/* 약 잔량 카드 */}
        <div className="dashboard-device__status-card dashboard-device__status-card--blue">
          <div className="dashboard-device__status-icon" aria-hidden="true">
            {/* 알약 아이콘 */}
            <svg
              viewBox="0 0 24 24"
              width="42"
              height="42"
              fill="none"
              stroke="#2563eb"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <g transform="rotate(-45 12 12)">
                <rect x="5" y="8.5" width="14" height="7" rx="3.5" />
                <line x1="12" y1="8.5" x2="12" y2="15.5" />
              </g>
            </svg>
          </div>
          <p className="dashboard-device__label">남은 복용 횟수</p>
          <p className="dashboard-device__value dashboard-device__value--blue">
            {deviceStatus.medication_level}
          </p>
        </div>
      </div>

      <div className="dashboard-device__meta">
        <div>
          <p className="dashboard-device__meta-label">마지막 동기화</p>
          <p className="dashboard-device__meta-value">{deviceStatus.last_sync_time}</p>
        </div>

        <div>
          <p className="dashboard-device__meta-label">다음 복약 시간</p>
          <p className="dashboard-device__meta-value">{deviceStatus.next_schedule_time}</p>
        </div>
      </div>
    </section>
  )
}

export default DeviceStatusSection
