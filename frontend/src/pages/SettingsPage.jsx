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
import {
  accountActionItems,
  initialGuardianInfo,
  initialSettings,
  settingsInfo,
} from '../data/settingsMock'
import '../styles/SettingsPage.css'
import '../styles/MobileBottomNav.css'

function SettingsPage() {
  const [settings, setSettings] = useState(initialSettings)
  const [guardianInfo, setGuardianInfo] = useState(initialGuardianInfo)
  const [isGuardianModalOpen, setIsGuardianModalOpen] = useState(false)

  const handleToggle = (field) => {
    setSettings((prev) => ({
      ...prev,
      [field]: !prev[field],
    }))
  }

  const handleChangeValue = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }))
  }

  const handleCancel = () => {
    setSettings(initialSettings)
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

            <SettingsSectionCard title="알림 설정">
              <SettingToggleRow
                title="SMS 알림"
                description="복약 시간에 SMS로 알림을 전송합니다"
                checked={settings.smsEnabled}
                onChange={() => handleToggle('smsEnabled')}
              />

              <SettingTimeRow
                title="알림 시간 설정"
                description="복약 알림 받을 시간을 설정합니다"
                value={settings.alertTime}
                onChange={(value) => handleChangeValue('alertTime', value)}
              />
            </SettingsSectionCard>

            <SettingsSectionCard title="디바이스 설정">
              <SettingToggleRow
                title="자동 동기화"
                description="디바이스와 자동으로 데이터를 동기화합니다"
                checked={settings.autoSyncEnabled}
                onChange={() => handleToggle('autoSyncEnabled')}
              />

            <SettingsSliderRow
            title="알림 소리 크기"
            description="알림음의 볼륨을 조절합니다"
            value={settings.volume}
            onChange={(value) => handleChangeValue('volume', value)}
            />

              <SettingToggleRow
                title="음성 안내 설정"
                description="복약 알림 음성을 설정합니다"
                checked={settings.voiceGuideEnabled}
                onChange={() => handleToggle('voiceGuideEnabled')}
              />
            </SettingsSectionCard>

            <SettingsSectionCard title="계정 설정">
              {accountActionItems.map((item) => (
                <SettingActionRow
                  key={item.id}
                  title={item.title}
                  description={item.description}
                  buttonLabel={item.buttonLabel}
                onClick={() => {
                        if (item.title === '보호자 정보 수정') {
                            setIsGuardianModalOpen(true)
                            return
                        }

                alert(`${item.title} 기능은 나중에 연결 예정`)
            }}
                />
              ))}
            </SettingsSectionCard>

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
      {isGuardianModalOpen ? (
        <GuardianEditModal
            initialData={guardianInfo}
            onClose={() => setIsGuardianModalOpen(false)}
            onSave={(updatedGuardianInfo) => {
                setGuardianInfo(updatedGuardianInfo)
                setIsGuardianModalOpen(false)
                alert('보호자 정보가 저장되었습니다.')
            }}
        />
    ) : null}
    </div>
  )
}

export default SettingsPage