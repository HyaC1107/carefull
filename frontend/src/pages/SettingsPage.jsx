import { useEffect, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import SettingsHeader from '../components/settings/SettingsHeader'
import SettingsSectionCard from '../components/settings/SettingsSectionCard'
import SettingToggleRow from '../components/settings/SettingToggleRow'
import SettingActionRow from '../components/settings/SettingActionRow'
import GuardianEditModal from '../components/settings/GuardianEditModal'
import PatientEditModal from '../components/settings/PatientEditModal'
import { hasStoredToken, requestJson, TOKEN_STORAGE_KEY } from '../api'
import '../styles/SettingsPage.css'
import '../styles/MobileBottomNav.css'

const NOTIF_PREFS_KEY = 'carefull_notif_prefs'

const DEFAULT_NOTIF_PREFS = {
  MISSED: true,
  LOW_STOCK: true,
  ERROR: true,
  FAILED: true,
  SUCCESS: false,
}

const NOTIF_TOGGLE_ITEMS = [
  {
    key: 'MISSED',
    title: '미복약 알림',
    description: '복약 예정 시간이 지나도 복약 기록이 없을 때 알림을 표시합니다',
  },
  {
    key: 'LOW_STOCK',
    title: '약 부족 알림',
    description: '남은 약이 부족할 때 알림을 표시합니다',
  },
  {
    key: 'ERROR',
    title: '기기 오류 알림',
    description: '디스펜서 기기에 오류가 발생했을 때 알림을 표시합니다',
  },
  {
    key: 'FAILED',
    title: '복약 실패 알림',
    description: '복약 시도가 정상 완료되지 않았을 때 알림을 표시합니다',
  },
  {
    key: 'SUCCESS',
    title: '복약 완료 알림',
    description: '복약이 정상 완료될 때마다 알림을 표시합니다',
  },
]

const ACCOUNT_ACTION_ITEMS = [
  {
    id: 'patient',
    title: '환자 정보 수정',
    description: '환자의 기본 정보를 수정합니다',
    buttonLabel: '수정',
  },
  {
    id: 'guardian',
    title: '보호자 정보 수정',
    description: '보호자 연락처와 정보를 관리합니다',
    buttonLabel: '수정',
  },
  {
    id: 'logout',
    title: '로그아웃',
    description: '현재 로그인된 계정에서 로그아웃합니다',
    buttonLabel: '실행',
  },
]

function loadNotifPrefs() {
  try {
    const stored = localStorage.getItem(NOTIF_PREFS_KEY)
    if (stored) return { ...DEFAULT_NOTIF_PREFS, ...JSON.parse(stored) }
  } catch {}
  return { ...DEFAULT_NOTIF_PREFS }
}

function SettingsPage() {
  const [notifPrefs, setNotifPrefs] = useState(loadNotifPrefs)
  const [patientData, setPatientData] = useState(null)
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false)
  const [isGuardianModalOpen, setIsGuardianModalOpen] = useState(false)

  useEffect(() => {
    if (!hasStoredToken()) return

    requestJson('/api/patient/me', { auth: true })
      .then((res) => setPatientData(res?.patient || null))
      .catch((err) => console.error('settings patient fetch error:', err))
  }, [])

  const handleToggleNotif = (key) => {
    setNotifPrefs((prev) => {
      const next = { ...prev, [key]: !prev[key] }
      localStorage.setItem(NOTIF_PREFS_KEY, JSON.stringify(next))
      return next
    })
  }

  const handleSavePatient = async (updatedFields) => {
    const payload = { ...patientData, ...updatedFields }
    const res = await requestJson('/api/patient/me', {
      method: 'PUT',
      auth: true,
      body: payload,
    })
    setPatientData(res?.patient || patientData)
    setIsPatientModalOpen(false)
  }

  const handleSaveGuardian = async (updatedFields) => {
    const payload = { ...patientData, ...updatedFields }
    const res = await requestJson('/api/patient/me', {
      method: 'PUT',
      auth: true,
      body: payload,
    })
    setPatientData(res?.patient || patientData)
    setIsGuardianModalOpen(false)
  }

  const handleAccountAction = (id) => {
    if (id === 'patient') {
      if (!patientData) {
        alert('환자 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.')
        return
      }
      setIsPatientModalOpen(true)
    } else if (id === 'guardian') {
      if (!patientData) {
        alert('환자 정보를 불러오는 중입니다. 잠시 후 다시 시도해주세요.')
        return
      }
      setIsGuardianModalOpen(true)
    } else if (id === 'logout') {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      window.location.href = '/'
    }
  }

  return (
    <div className="settings-page">
      <div className="settings-layout">
        <Sidebar activeMenu="settings" />

        <div className="settings-main">
          <TopHeader />

          <main className="settings-content">
            <SettingsHeader />

            <SettingsSectionCard title="알림 수신 설정">
              {NOTIF_TOGGLE_ITEMS.map((item) => (
                <SettingToggleRow
                  key={item.key}
                  title={item.title}
                  description={item.description}
                  checked={notifPrefs[item.key]}
                  onChange={() => handleToggleNotif(item.key)}
                />
              ))}
            </SettingsSectionCard>

            <SettingsSectionCard title="계정 설정">
              {ACCOUNT_ACTION_ITEMS.map((item) => (
                <SettingActionRow
                  key={item.id}
                  title={item.title}
                  description={item.description}
                  buttonLabel={item.buttonLabel}
                  onClick={() => handleAccountAction(item.id)}
                />
              ))}
            </SettingsSectionCard>
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="settings" />

      {isPatientModalOpen && patientData ? (
        <PatientEditModal
          initialData={patientData}
          onClose={() => setIsPatientModalOpen(false)}
          onSave={handleSavePatient}
        />
      ) : null}

      {isGuardianModalOpen && patientData ? (
        <GuardianEditModal
          initialData={{
            guardian_name: patientData.guardian_name || '',
            guardian_phone: patientData.guardian_phone || '',
          }}
          onClose={() => setIsGuardianModalOpen(false)}
          onSave={handleSaveGuardian}
        />
      ) : null}
    </div>
  )
}

export default SettingsPage
