import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import PatientProfileCard from '../components/patient/PatientProfileCard'
import MedicationListCard from '../components/patient/MedicationListCard'
import DeviceInfoCard from '../components/patient/DeviceInfoCard'
import {
  deviceDetail,
  deviceStatusList,
  medications,
  patientProfile,
} from '../data/patientMock'
import '../styles/PatientPage.css'
import '../styles/MobileBottomNav.css'

function PatientPage() {
  return (
    <div className="patient-page">
      <div className="patient-layout">
        <Sidebar activeMenu="patient" />

        <div className="patient-main">
          <TopHeader />

          <main className="patient-content">
            <section className="patient-page-header">
              <h2 className="patient-page-header__title">환자 정보</h2>
              <p className="patient-page-header__subtitle">
                환자의 기본 정보와 복용 약물 정보를 관리합니다
              </p>
            </section>

            <PatientProfileCard profile={patientProfile} />
            <MedicationListCard medications={medications} />
            <DeviceInfoCard
              statusList={deviceStatusList}
              detail={deviceDetail}
            />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="patient" />
    </div>
  )
}

export default PatientPage