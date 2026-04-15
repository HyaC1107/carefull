import { useState } from 'react'
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
  deviceDetail,
  deviceStatusList,
  medications,
  patientProfile,
} from '../data/patientMock'
import '../styles/PatientPage.css'
import '../styles/MobileBottomNav.css'

function PatientPage() {
  // 지금은 mock 기준으로 "미등록 상태"부터 시작
  const [patientData, setPatientData] = useState(null)
  const [deviceData, setDeviceData] = useState(null)

  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState(false)
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false)

  const hasPatient = Boolean(patientData)
  const hasDevice = Boolean(deviceData)

  const handleDeviceRegisterSuccess = (newDevice) => {
    setDeviceData(newDevice)
    setIsDeviceModalOpen(false)
  }

  const handlePatientRegisterSuccess = (newPatient) => {
    setPatientData({
      ...patientProfile,
      name: newPatient.name || patientProfile.name,
      ageGenderBlood:
        `${newPatient.birthDate ? newPatient.birthDate : '76세'} · ${newPatient.gender || '여성'} · ${newPatient.bloodType || '혈액형 A형'}`,
      phone: newPatient.phone || patientProfile.phone,
      address: newPatient.address || patientProfile.address,
      guardianName: newPatient.guardianName
        ? `${newPatient.guardianName} (보호자)`
        : patientProfile.guardianName,
      guardianPhone: newPatient.guardianPhone || patientProfile.guardianPhone,
      physicalInfo:
        `${newPatient.height ? `키 ${newPatient.height}cm` : '키 158cm'} · ${
          newPatient.weight ? `체중 ${newPatient.weight}kg` : '체중 62kg'
        }`,
    })

    setIsPatientModalOpen(false)
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
                  statusList={deviceStatusList}
                  detail={{
                    ...deviceDetail,
                    serialNumber:
                      deviceData?.serialNumber || deviceDetail.serialNumber,
                  }}
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

export default PatientPage