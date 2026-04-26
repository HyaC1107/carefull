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
  const [isPatientRegistered, setIsPatientRegistered] = useState(false)
  const [isDeviceRegistered, setIsDeviceRegistered] = useState(false)
  const [isRegistrationCheckLoading, setIsRegistrationCheckLoading] =
    useState(true)
  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState(false)
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false)
  const [isDeviceRegistrationCompleted, setIsDeviceRegistrationCompleted] =
    useState(false)

  useEffect(() => {
    const fetchPatientPageData = async () => {
      if (!hasStoredToken()) {
        setIsRegistrationCheckLoading(false)
        return
      }

      try {
        const [patientResponse, deviceResponse, scheduleResponse] =
          await Promise.all([
            requestJson('/api/patient/me', { auth: true }).catch(() => null),
            requestJson('/api/device/me', { auth: true }).catch(() => null),
            requestJson('/api/schedule', { auth: true }).catch(() => null),
          ])

        const nickname = getStoredAuthPayload()?.nick || '등록 사용자'

        const patient = patientResponse?.patient ?? null
        const device = deviceResponse?.device ?? null

        setIsPatientRegistered(hasRegisteredPatient(patient))
        setIsDeviceRegistered(hasRegisteredDevice(device))
        setPatientData(mapPatientProfile(patient, nickname))
        setDeviceData(mapDeviceDetail(device))
        setMedications(mapPatientMedications(scheduleResponse?.schedules))
      } catch (error) {
        console.error('patient page fetch error:', error)
      } finally {
        setIsRegistrationCheckLoading(false)
      }
    }

    fetchPatientPageData()
  }, [])

  const hasDevice = isDeviceRegistered || Boolean(pendingDevice)
  const shouldShowPatientDetail =
    !isRegistrationCheckLoading && isPatientRegistered && isDeviceRegistered
  const shouldShowRegistrationGate =
    !isRegistrationCheckLoading &&
    (!isPatientRegistered || !isDeviceRegistered)

  const handleDeviceRegisterSuccess = async (newDevice) => {
    const nextDevice = {
      device_uid: newDevice.device_uid?.trim() || '',
      deviceName: newDevice.deviceName?.trim() || '',
    }

    if (isPatientRegistered && hasStoredToken()) {
      try {
        console.log('[device-register] request:', {
          device_uid: nextDevice.device_uid,
          device_name: nextDevice.deviceName,
        })
        const deviceResponse = await requestJson('/api/device/register', {
          method: 'POST',
          auth: true,
          body: {
            device_uid: nextDevice.device_uid,
            device_name: nextDevice.deviceName,
          },
        })

        setDeviceData(mapDeviceDetail(deviceResponse?.device))
        setIsDeviceRegistered(hasRegisteredDevice(deviceResponse?.device))
        setIsDeviceRegistrationCompleted(true)
        setPendingDevice(null)
        setIsDeviceModalOpen(false)
      } catch (error) {
        console.error('device register error:', error)
        alert(error.message || 'Device registration failed.')
      }
      return
    }

    setPendingDevice(nextDevice)
    setIsDeviceRegistrationCompleted(true)
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
          phone: newPatient.phone || '',
          address: newPatient.address || '',
          bloodtype: newPatient.bloodtype || '',
          height: toNumber(newPatient.height),
          weight: toNumber(newPatient.weight),
          guardian_name: newPatient.guardian_name || '',
          guardian_phone: newPatient.guardian_phone || '',
          device_uid: pendingDevice.device_uid,
          device_name: pendingDevice.deviceName,
        },
      })

      const [patientResponse, deviceResponse] = await Promise.all([
        requestJson('/api/patient/me', { auth: true }),
        requestJson('/api/device/me', { auth: true }).catch(() => null),
      ])

      const syncedPatientResponse =
        shouldSyncPatientProfile(newPatient) && patientResponse?.patient
          ? await requestJson('/api/patient/me', {
              method: 'PUT',
              auth: true,
              body: buildPatientUpdatePayload(patientResponse.patient, newPatient),
            }).catch((error) => {
              console.error('patient profile sync error:', error)
              return null
            })
          : null

      const nickname = getStoredAuthPayload()?.nick || '등록 사용자'

      setPatientData(
        mapPatientProfile(
          syncedPatientResponse?.patient || patientResponse?.patient,
          nickname,
        ),
      )
      setDeviceData(mapDeviceDetail(deviceResponse?.device))
      setIsPatientRegistered(
        hasRegisteredPatient(
          syncedPatientResponse?.patient || patientResponse?.patient,
        ),
      )
      setIsDeviceRegistered(hasRegisteredDevice(deviceResponse?.device))
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
            {isRegistrationCheckLoading ? (
              <section className="patient-page-header">
                <h2 className="patient-page-header__title">환자 정보</h2>
                <p className="patient-page-header__subtitle">
                  환자 등록 상태를 불러오고 있습니다.
                </p>
              </section>
            ) : null}

            {shouldShowRegistrationGate ? (
              <PatientEmptyState
                hasDevice={hasDevice}
                isDeviceRegistrationCompleted={isDeviceRegistrationCompleted}
                onOpenDeviceModal={() => setIsDeviceModalOpen(true)}
                onOpenPatientModal={() => setIsPatientModalOpen(true)}
              />
            ) : null}

            {shouldShowPatientDetail ? (
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
            ) : null}
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

function hasRegisteredPatient(patient) {
  return Boolean(patient?.patient_id)
}

function hasRegisteredDevice(device) {
  return Boolean(device?.device_id || device?.device_uid)
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

function mapPatientMedications(schedules = []) {
  return schedules.map((schedule) => ({
    id: schedule.sche_id,
    medi_name: schedule.medi_name || `약물 ${schedule.medi_id}`,
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

function shouldSyncPatientProfile(patient) {
  return [
    patient?.patient_name,
    patient?.birthdate,
    patient?.gender,
    patient?.bloodtype,
    patient?.height,
    patient?.weight,
    patient?.phone,
    patient?.address,
    patient?.guardian_name,
    patient?.guardian_phone,
  ].every((value) => String(value ?? '').trim())
}

function buildPatientUpdatePayload(currentPatient, newPatient) {
  return {
    patient_name: newPatient.patient_name,
    birthdate: newPatient.birthdate,
    gender: newPatient.gender,
    phone: newPatient.phone,
    address: newPatient.address,
    bloodtype: newPatient.bloodtype,
    height: toNumber(newPatient.height),
    weight: toNumber(newPatient.weight),
    fingerprint_id: currentPatient?.fingerprint_id ?? 0,
    guardian_name: newPatient.guardian_name,
    guardian_phone: newPatient.guardian_phone,
  }
}

export default PatientPage
