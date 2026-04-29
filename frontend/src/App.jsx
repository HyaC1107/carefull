import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import SocialCallbackPage from './pages/SocialCallbackPage'
import DashboardPage from './pages/DashboardPage'
import SchedulePage from './pages/SchedulePage'
import StatsPage from './pages/StatsPage'
import AlertsPage from './pages/AlertsPage'
import PatientPage from './pages/PatientPage'
import SettingsPage from './pages/SettingsPage'
import { useFCM } from './hooks/useFCM'
import { hasStoredToken } from './api'
import { registerFcmTokenForCurrentUser } from './firebase-messaging'
import { HeaderDataProvider } from './context/HeaderDataContext'


import AdminLoginPage from './pages/AdminLoginPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import { hasAdminToken } from './adminApi'

function App() {
  useFCM()

  return (
    <HeaderDataProvider>
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/callback/:provider" element={<SocialCallbackPage />} />

      {/* 대시보드 페이지 */}
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />

      {/* 복약일정 페이지 */}
      <Route path="/schedule" element={<ProtectedRoute><SchedulePage /></ProtectedRoute>} />

      {/* 통계 페이지 */}
      <Route path="/stats" element={<ProtectedRoute><StatsPage /></ProtectedRoute>} />

      {/* 알림 페이지 */}
      <Route path="/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />

      {/* 환자정보 페이지 */}
      <Route path="/patient" element={<ProtectedRoute><PatientPage /></ProtectedRoute>} />
      <Route path="/register-patient" element={<ProtectedRoute><PatientPage /></ProtectedRoute>} />

      {/* 설정 페이지 */}
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

      {/* 관리자 페이지 */}
      <Route path="/admin" element={<AdminLoginPage />} />
      <Route path="/admin/dashboard" element={<AdminProtectedRoute><AdminDashboardPage /></AdminProtectedRoute>} />

      {/* 없는 주소로 들어오면 로그인 페이지로 보냄 */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
    </HeaderDataProvider>
  )
}

function ProtectedRoute({ children }) {
  useEffect(() => {
    registerFcmTokenForCurrentUser()
  }, [])

  if (!hasStoredToken()) {
    return <Navigate to="/login" replace />
  }
  return children
}

function AdminProtectedRoute({ children }) {
  if (!hasAdminToken()) {
    return <Navigate to="/admin" replace />
  }
  return children
}

export default App
