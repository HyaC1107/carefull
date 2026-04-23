import { useEffect, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import PatientProfileCard from '../components/patient/PatientProfileCard'
import MedicationListCard from '../components/patient/MedicationListCard'
import DeviceInfoCard from '../components/patient/DeviceInfoCard'
import PatientEmptyState from '../components/patient/PatientEmptyState'
import DeviceRegisterModal from '../components/patient/DeviceRegisterModal'
import PatientRegisterModal from '../components/patient/PatientRegisterModal'
import {
  getStoredAuthPayload,
  hasStoredToken,
  requestJson,
} from '../api'
import '../styles/PatientPage.css'
import '../styles/MobileBottomNav.css'

const DEFAULT_DEVICE_DETAIL = {
  modelName: 'Carefull Device',
  device_uid: '-',
  registered_at: '-',
  firmwareVersion: '-',
}

function PatientPage() {
  const [patientData, setPatientData] = useState(null)
  const [deviceData, setDeviceData] = useState(null)
  const [medications, setMedications] = useState([])
  const [pendingDevice, setPendingDevice] = useState(null)
  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState(false)
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false)

  useEffect(() => {
    const fetchPatientPageData = async () => {
      if (!hasStoredToken()) {
        return
      }

      try {
        const [patientResponse, deviceResponse, scheduleResponse, medicationResponse] =
          await Promise.all([
            requestJson('/api/patient/me', { auth: true }).catch(() => null),
            requestJson('/api/device/me', { auth: true }).catch(() => null),
            requestJson('/api/schedule', { auth: true }).catch(() => null),
            requestJson('/api/medication').catch(() => null),
          ])

        const nickname = getStoredAuthPayload()?.nick || '등록 사용자'

        setPatientData(mapPatientProfile(patientResponse?.patient, nickname))
        setDeviceData(mapDeviceDetail(deviceResponse?.device))
        setMedications(
          mapPatientMedications(
            scheduleResponse?.schedules,
            medicationResponse?.data,
          ),
        )
      } catch (error) {
        console.error('patient page fetch error:', error)
      }
    }

    fetchPatientPageData()
  }, [])

  const hasPatient = Boolean(patientData)
  const hasDevice = Boolean(deviceData || pendingDevice)

  const handleDeviceRegisterSuccess = (newDevice) => {
    setPendingDevice({
      device_uid: newDevice.device_uid?.trim() || '',
      deviceName: newDevice.deviceName?.trim() || '',
    })
    setIsDeviceModalOpen(false)
  }

  const handlePatientRegisterSuccess = async (newPatient) => {
    if (!pendingDevice?.device_uid || !hasStoredToken()) {
      return
    }

    try {
      await requestJson('/api/user/register-patient', {
        method: 'POST',
        auth: true,
        body: {
          patient_name: newPatient.patient_name || '',
          birthdate: newPatient.birthdate || '',
          gender: newPatient.gender || '',
          bloodtype: newPatient.bloodtype || '',
          height: toNumber(newPatient.height),
          weight: toNumber(newPatient.weight),
          device_uid: pendingDevice.device_uid,
        },
      })

      const [patientResponse, deviceResponse] = await Promise.all([
        requestJson('/api/patient/me', { auth: true }),
        requestJson('/api/device/me', { auth: true }).catch(() => null),
      ])

      const nickname = getStoredAuthPayload()?.nick || '등록 사용자'

      setPatientData(mapPatientProfile(patientResponse?.patient, nickname))
      setDeviceData(mapDeviceDetail(deviceResponse?.device))
      setPendingDevice(null)
      setIsPatientModalOpen(false)
    } catch (error) {
      console.error('patient register error:', error)
      alert(error.message || '환자 등록에 실패했습니다.')
    }
  }

  return (
    <div className="patient-page">
      <div className="patient-layout">
        <Sidebar activeMenu="patient" />

        <div className="patient-main">
          <TopHeader />

          <main className="patient-content">
            {!hasPatient ? (
              <PatientEmptyState
                hasDevice={hasDevice}
                onOpenDeviceModal={() => setIsDeviceModalOpen(true)}
                onOpenPatientModal={() => setIsPatientModalOpen(true)}
              />
            ) : (
              <>
                <section className="patient-page-header">
                  <h2 className="patient-page-header__title">환자 정보</h2>
                  <p className="patient-page-header__subtitle">
                    환자의 기본 정보와 복용 약물 정보를 관리합니다
                  </p>
                </section>

                <PatientProfileCard profile={patientData} />
                <MedicationListCard medications={medications} />
                <DeviceInfoCard
                  statusList={buildDeviceStatusList(deviceData)}
                  detail={deviceData?.detail || DEFAULT_DEVICE_DETAIL}
                />
              </>
            )}
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="patient" />

      {isDeviceModalOpen ? (
        <DeviceRegisterModal
          onClose={() => setIsDeviceModalOpen(false)}
          onSuccess={handleDeviceRegisterSuccess}
        />
      ) : null}

      {isPatientModalOpen ? (
        <PatientRegisterModal
          onClose={() => setIsPatientModalOpen(false)}
          onSuccess={handlePatientRegisterSuccess}
        />
      ) : null}
    </div>
  )
}

function mapPatientProfile(patient, nickname) {
  if (!patient) {
    return null
  }

  return {
    patient_name: patient.patient_name || nickname || '등록 사용자',
    ageGenderBlood: `${patient.birthdate || '-'} · ${patient.gender || '-'} · ${
      patient.bloodtype || '-'
    }`,
    phone: patient.phone || '-',
    address: patient.address || '-',
    guardian_name: patient.guardian_name || '-',
    guardian_phone: patient.guardian_phone || '-',
    created_at: formatDate(patient.created_at),
    physicalInfo: `키 ${patient.height ?? '-'}cm · 체중 ${
      patient.weight ?? '-'
    }kg`,
  }
}

function mapDeviceDetail(device) {
  if (!device) {
    return null
  }

  return {
    detail: {
      modelName: 'Carefull Device',
      device_uid: device.device_uid || '-',
      registered_at: formatDate(device.registered_at),
      firmwareVersion: '-',
    },
    is_connected: Boolean(device.is_connected),
    device_status: device.device_status || '-',
    last_ping: formatDate(device.last_ping),
  }
}

function buildDeviceStatusList(deviceData) {
  if (!deviceData) {
    return [
      { id: 'connection', label: '연결 상태', value: '미연결', type: 'success' },
      { id: 'status', label: '디바이스 상태', value: '-', type: 'primary' },
      { id: 'sync', label: '마지막 동기화', value: '-', type: 'info' },
    ]
  }

  return [
    {
      id: 'connection',
      label: '연결 상태',
      value: deviceData.is_connected ? '연결됨' : '연결 안 됨',
      type: 'success',
    },
    {
      id: 'status',
      label: '디바이스 상태',
      value: deviceData.device_status,
      type: 'primary',
    },
    {
      id: 'sync',
      label: '마지막 동기화',
      value: deviceData.last_ping,
      type: 'info',
    },
  ]
}

function mapPatientMedications(schedules = [], medications = []) {
  const medicationMap = medications.reduce((acc, item) => {
    acc[item.medi_id] = item.medi_name
    return acc
  }, {})

  return schedules.map((schedule) => ({
    id: schedule.sche_id,
    medi_name: medicationMap[schedule.medi_id] || `약물 ${schedule.medi_id}`,
    ingredient: `약물 ID ${schedule.medi_id}`,
    start_date: formatDate(schedule.start_date),
    time_to_take: formatTime(schedule.time_to_take),
    amount:
      Number(schedule.dose_interval) > 1
        ? `${schedule.dose_interval}일 간격`
        : '매일 복용',
    timing: schedule.end_date
      ? `${formatDate(schedule.end_date)}까지`
      : '종료일 없음',
  }))
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return date.toLocaleDateString('ko-KR')
}

function formatTime(value) {
  if (!value) {
    return '-'
  }

  return String(value).slice(0, 5)
}

function toNumber(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export default PatientPage
