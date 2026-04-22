function DeviceStatusBox({ item }) {
  return (
    <div className={`patient-device-status-box patient-device-status-box--${item.type}`}>
      <p className="patient-device-status-box__label">{item.label}</p>
      <p className="patient-device-status-box__value">{item.value}</p>
    </div>
  )
}

export default DeviceStatusBox