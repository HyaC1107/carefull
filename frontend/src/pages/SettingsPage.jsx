import { useEffect, useRef, useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import SettingsHeader from '../components/settings/SettingsHeader'
import SettingsSectionCard from '../components/settings/SettingsSectionCard'
import SettingToggleRow from '../components/settings/SettingToggleRow'
import SettingActionRow from '../components/settings/SettingActionRow'
import GuardianEditModal from '../components/settings/GuardianEditModal'
import PatientEditModal from '../components/settings/PatientEditModal'
import VoiceUploadTab from '../components/settings/VoiceUploadTab'
import AlarmSoundTab from '../components/settings/AlarmSoundTab'
import { hasStoredToken, requestJson, TOKEN_STORAGE_KEY } from '../api'
import { useUnreadCount } from '../hooks/useUnreadCount'
import '../styles/SettingsPage.css'
import '../styles/MobileBottomNav.css'

const NOTIF_PREFS_KEY = 'carefull_notif_prefs'

const DEFAULT_NOTIF_PREFS = {
  MISSED: true,
  LOW_STOCK: true,
  ERROR: true,
  FAILED: true,
  SUCCESS: true,
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

const TABS = [
  { key: 'general', label: '일반 설정' },
  { key: 'notification', label: '알림 설정' },
  { key: 'alarm', label: '알림음' },
  { key: 'voice', label: '보호자 목소리' },
]

function loadNotifPrefs() {
  try {
    const stored = localStorage.getItem(NOTIF_PREFS_KEY)
    if (stored) return { ...DEFAULT_NOTIF_PREFS, ...JSON.parse(stored) }
  } catch {
    // Ignore malformed stored preferences and fall back to defaults.
  }
  return { ...DEFAULT_NOTIF_PREFS }
}

function SettingsPage() {
  const unreadCount = useUnreadCount()
  const [activeTab, setActiveTab] = useState('general')
  const [notifPrefs, setNotifPrefs] = useState(loadNotifPrefs)
  const [notificationPermission, setNotificationPermission] = useState(
    getNotificationPermission,
  )
  const [patientData, setPatientData] = useState(null)
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false)
  const [isGuardianModalOpen, setIsGuardianModalOpen] = useState(false)
  const [isNotifSaved, setIsNotifSaved] = useState(false)
  const notifSaveTimerRef = useRef(null)
  const areAllNotifEnabled = NOTIF_TOGGLE_ITEMS.every(
    (item) => notifPrefs[item.key],
  )
  const isNotificationSupported = notificationPermission !== 'unsupported'

  useEffect(() => {
    if (!hasStoredToken()) return
    requestJson('/api/patient/me', { auth: true })
      .then((res) => setPatientData(res?.patient || null))
      .catch((err) => console.error('settings patient fetch error:', err))
  }, [])

  useEffect(() => {
    return () => {
      if (notifSaveTimerRef.current) {
        clearTimeout(notifSaveTimerRef.current)
      }
    }
  }, [])

  const handleToggleNotif = (key) => {
    setIsNotifSaved(false)
    setNotifPrefs((prev) => {
      return { ...prev, [key]: !prev[key] }
    })
  }

  const handleToggleAllNotif = () => {
    const nextChecked = !areAllNotifEnabled
    setIsNotifSaved(false)

    setNotifPrefs(
      NOTIF_TOGGLE_ITEMS.reduce(
        (acc, item) => ({
          ...acc,
          [item.key]: nextChecked,
        }),
        { ...notifPrefs },
      ),
    )
  }

  const handleSaveNotifPrefs = () => {
    localStorage.setItem(NOTIF_PREFS_KEY, JSON.stringify(notifPrefs))
    setIsNotifSaved(true)

    if (notifSaveTimerRef.current) {
      clearTimeout(notifSaveTimerRef.current)
    }

    notifSaveTimerRef.current = window.setTimeout(() => {
      setIsNotifSaved(false)
      notifSaveTimerRef.current = null
    }, 1800)
  }

  const handleRequestNotificationPermission = async () => {
    if (!('Notification' in window)) {
      setNotificationPermission('unsupported')
      return
    }

    const permission = await Notification.requestPermission()
    setNotificationPermission(permission)
  }

  const handleSavePatient = async (updatedFields) => {
    const res = await requestJson('/api/patient/me', {
      method: 'PATCH',
      auth: true,
      body: {
        patient_name: updatedFields.patient_name,
        birthdate: updatedFields.birthdate,
        gender: updatedFields.gender,
        phone: updatedFields.phone,
        address: updatedFields.address,
        bloodtype: updatedFields.bloodtype,
        height: updatedFields.height,
        weight: updatedFields.weight,
      },
    })
    setPatientData(res?.patient || patientData)
    setIsPatientModalOpen(false)
    window.dispatchEvent(new Event('carefull:top-header-refresh'))
  }

  const handleSaveGuardian = async (updatedFields) => {
    const res = await requestJson('/api/patient/guardian', {
      method: 'PATCH',
      auth: true,
      body: {
        guardian_name: updatedFields.guardian_name,
        guardian_phone: updatedFields.guardian_phone,
      },
    })
    setPatientData(res?.patient || patientData)
    setIsGuardianModalOpen(false)
    window.dispatchEvent(new Event('carefull:top-header-refresh'))
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
      sessionStorage.removeItem('carefull_fcm_registered')
      window.location.assign('/')
    }
  }

  return (
    <div className="settings-page">
      <div className="settings-layout">
        <Sidebar activeMenu="settings" alertCount={unreadCount} />

        <div className="settings-main">
          <TopHeader />

          <main className="settings-content">
            <SettingsHeader />

<nav className="settings-tabs">
  {TABS.map((tab) => (
    <button
      key={tab.key}
      className={`settings-tab-btn${activeTab === tab.key ? ' settings-tab-btn--active' : ''}`}
      onClick={() => setActiveTab(tab.key)}
    >
      {tab.label}
    </button>
  ))}
</nav>

{activeTab === 'notification' && (
  <>
    <SettingsSectionCard title="알림 수신 설정">
      <SettingToggleRow
        title="전체 알림"
        description="모든 알림 항목의 수신 여부를 한 번에 설정합니다."
        checked={areAllNotifEnabled}
        onChange={handleToggleAllNotif}
      />

      {NOTIF_TOGGLE_ITEMS.map((item) => (
        <SettingToggleRow
          key={item.key}
          title={item.title}
          description={item.description}
          checked={notifPrefs[item.key]}
          onChange={() => handleToggleNotif(item.key)}
        />
      ))}

      <div className="settings-section-actions">
        <button
          type="button"
          className="settings-footer-actions__button settings-footer-actions__button--primary"
          onClick={handleSaveNotifPrefs}
        >
          {isNotifSaved ? '반영됨' : '변경사항 반영'}
        </button>
      </div>
    </SettingsSectionCard>

    <SettingsSectionCard title="브라우저 알림 권한">
      <div className="settings-row settings-row--action">
        <div className="settings-row__text">
          <p className="settings-row__title">
            현재 상태: {getNotificationPermissionText(notificationPermission)}
          </p>
          <p className="settings-row__description">
            {getNotificationPermissionDescription(notificationPermission)}
          </p>
        </div>

        {isNotificationSupported && notificationPermission === 'default' ? (
          <button
            type="button"
            className="settings-action-button"
            onClick={handleRequestNotificationPermission}
          >
            알림 권한 요청
          </button>
        ) : null}
      </div>
    </SettingsSectionCard>
  </>
)}

            {activeTab === 'general' && (
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
            )}

            {activeTab === 'alarm' && (
              <SettingsSectionCard title="알림음 설정">
                <AlarmSoundTab />
              </SettingsSectionCard>
            )}

            {activeTab === 'voice' && (
              <SettingsSectionCard title="보호자 목소리 등록">
                <VoiceUploadTab />
              </SettingsSectionCard>
            )}
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

function getNotificationPermission() {
  if (!('Notification' in window)) {
    return 'unsupported'
  }

  return Notification.permission
}

function getNotificationPermissionText(permission) {
  if (permission === 'granted') {
    return '허용됨'
  }

  if (permission === 'denied') {
    return '차단됨'
  }

  if (permission === 'unsupported') {
    return '지원하지 않음'
  }

  return '미설정'
}

function getNotificationPermissionDescription(permission) {
  if (permission === 'denied') {
    return '브라우저 사이트 설정에서 직접 변경해야 합니다.'
  }

  if (permission === 'unsupported') {
    return '이 브라우저는 Notification API를 지원하지 않습니다.'
  }

  if (permission === 'granted') {
    return '브라우저 알림을 받을 수 있는 상태입니다.'
  }

  return '알림 권한 요청 버튼을 눌러 브라우저 알림을 허용할 수 있습니다.'
}

export default SettingsPage
