import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import SchedulePage from './pages/SchedulePage'
import StatsPage from './pages/StatsPage'
import AlertsPage from './pages/AlertsPage'
import PatientPage from './pages/PatientPage'

function App() {
  return (
    <Routes>
      {/* 기본 주소로 들어오면 로그인 페이지로 보냄 */}
      <Route path="/" element={<Navigate to="/login" replace />} />

      {/* 로그인 페이지 */}
      <Route path="/login" element={<LoginPage />} />

      {/* 대시보드 페이지 */}
      <Route path="/dashboard" element={<DashboardPage />} />

      {/* 복약일정 페이지 */}
      <Route path="/schedule" element={<SchedulePage />} />

      {/* 통계 페이지 */}
      <Route path="/stats" element={<StatsPage />} />

      {/* 알림 페이지 */}
      <Route path="/alerts" element={<AlertsPage />} />

      {/* 환자정보 페이지 */}
      <Route path="/patient" element={<PatientPage />} />

      {/* 없는 주소로 들어오면 로그인 페이지로 보냄 */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App