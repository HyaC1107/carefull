import { useState } from 'react'
import Sidebar from '../components/layout/Sidebar'
import TopHeader from '../components/layout/TopHeader'
import MobileBottomNav from '../components/layout/MobileBottomNav'
import SettingsHeader from '../components/settings/SettingsHeader'
import SettingsSectionCard from '../components/settings/SettingsSectionCard'
import SettingToggleRow from '../components/settings/SettingToggleRow'
import SettingTimeRow from '../components/settings/SettingTimeRow'
import SettingsSliderRow from '../components/settings/SettingsSliderRow'
import SettingActionRow from '../components/settings/SettingActionRow'
import SettingsInfoBanner from '../components/settings/SettingsInfoBanner'
import SettingsFooterActions from '../components/settings/SettingsFooterActions'
import GuardianEditModal from '../components/settings/GuardianEditModal'
import PatientEditModal from '../components/settings/PatientEditModal'
import VoiceUploadTab from '../components/settings/VoiceUploadTab'
import { 
  accountActionItems, 
  initialGuardianInfo, 
  initialSettings, 
  settingsInfo 
} from '../data/settingsMock'
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

function loadNotifPrefs() {
  try {
    const stored = localStorage.getItem(NOTIF_PREFS_KEY)
    if (stored) return { ...DEFAULT_NOTIF_PREFS, ...JSON.parse(stored) }
  } catch {}
  return { ...DEFAULT_NOTIF_PREFS }
}

const TABS = [
  { key: 'general', label: '일반 설정' },
  { key: 'voice', label: '보호자 목소리' },
]

function SettingsPage() {
  const [activeTab, setActiveTab] = useState('general')
  const [notifPrefs, setNotifPrefs] = useState(loadNotifPrefs)
  const [settings, setSettings] = useState(initialSettings)
  const [guardianInfo, setGuardianInfo] = useState(initialGuardianInfo)
  const [isGuardianModalOpen, setIsGuardianModalOpen] = useState(false)
  const [isPatientModalOpen, setIsPatientModalOpen] = useState(false)

  const handleToggleNotif = (key) => {
    setNotifPrefs(prev => {
      const next = { ...prev, [key]: !prev[key] }
      localStorage.setItem(NOTIF_PREFS_KEY, JSON.stringify(next))
      return next
    })
  }

  const handleToggleSetting = (field) => {
    setSettings((prev) => ({
      ...prev,
      [field]: !prev[field],
    }))
  }

  const handleChangeSettingValue = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleAccountAction = (id, title) => {
    if (id === 'guardian' || title === '보호자 정보 수정') {
      setIsGuardianModalOpen(true)
      return
    }
    if (id === 'patient' || title === '환자 정보 수정') {
      setIsPatientModalOpen(true)
      return
    }
    alert(`${title} 기능은 나중에 연결 예정`)
  }

  const handleCancel = () => {
    setSettings(initialSettings)
    setNotifPrefs(loadNotifPrefs())
  }

  const handleSave = () => {
    alert('설정이 저장되었습니다.')
  }

  return (
    <div className="settings-page">
      <div className="settings-layout">
        <Sidebar activeMenu="settings" />

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

            {activeTab === 'general' && (
              <>
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
                  
                  <div style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '20px' }}>
                    <SettingToggleRow
                      title="SMS 알림"
                      description="복약 시간에 SMS로 알림을 전송합니다"
                      checked={settings.smsEnabled}
                      onChange={() => handleToggleSetting('smsEnabled')}
                    />

                    <SettingTimeRow
                      title="알림 시간 설정"
                      description="복약 알림 받을 시간을 설정합니다"
                      value={settings.alertTime}
                      onChange={(value) => handleChangeSettingValue('alertTime', value)}
                    />
                  </div>
                </SettingsSectionCard>

                <SettingsSectionCard title="디바이스 설정">
                  <SettingToggleRow
                    title="자동 동기화"
                    description="디바이스와 자동으로 데이터를 동기화합니다"
                    checked={settings.autoSyncEnabled}
                    onChange={() => handleToggleSetting('autoSyncEnabled')}
                  />

                  <SettingsSliderRow
                    title="알림 소리 크기"
                    description="알림음의 볼륨을 조절합니다"
                    value={settings.volume}
                    onChange={(value) => handleChangeSettingValue('volume', value)}
                  />

                  <SettingToggleRow
                    title="음성 안내 설정"
                    description="복약 알림 음성을 설정합니다"
                    checked={settings.voiceGuideEnabled}
                    onChange={() => handleToggleSetting('voiceGuideEnabled')}
                  />
                </SettingsSectionCard>

                <SettingsSectionCard title="계정 설정">
                  {accountActionItems.map((item) => (
                    <SettingActionRow
                      key={item.id}
                      title={item.title}
                      description={item.description}
                      buttonLabel={item.buttonLabel}
                      onClick={() => handleAccountAction(item.id, item.title)}
                    />
                  ))}
                </SettingsSectionCard>
              </>
            )}

            {activeTab === 'voice' && (
              <SettingsSectionCard title="보호자 목소리 등록">
                <VoiceUploadTab />
              </SettingsSectionCard>
            )}

            <SettingsInfoBanner
              title={settingsInfo.title}
              description={settingsInfo.description}
            />

            <SettingsFooterActions
              onCancel={handleCancel}
              onSave={handleSave}
            />
          </main>
        </div>
      </div>

      <MobileBottomNav activeMenu="settings" />
      
      {isGuardianModalOpen && (
        <GuardianEditModal
          initialData={guardianInfo}
          onClose={() => setIsGuardianModalOpen(false)}
          onSave={(updatedGuardianInfo) => {
            setGuardianInfo(updatedGuardianInfo)
            setIsGuardianModalOpen(false)
            alert('보호자 정보가 저장되었습니다.')
          }}
        />
      )}

      {isPatientModalOpen && (
        <PatientEditModal
          onClose={() => setIsPatientModalOpen(false)}
          onSave={(updatedPatientData) => {
            setIsPatientModalOpen(false)
            alert('환자 정보가 저장되었습니다.')
          }}
        />
      )}
    </div>
  )
}

export default SettingsPage
