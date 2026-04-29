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

function ProtectedRoute({ children }) {
  if (!hasStoredToken()) {
    return <Navigate to="/login" replace />
  }
  return children
}

function App() {
  useFCM()

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/callback/:provider" element={<SocialCallbackPage />} />

      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/schedule"  element={<ProtectedRoute><SchedulePage /></ProtectedRoute>} />
      <Route path="/stats"     element={<ProtectedRoute><StatsPage /></ProtectedRoute>} />
      <Route path="/alerts"    element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
      <Route path="/patient"   element={<ProtectedRoute><PatientPage /></ProtectedRoute>} />
      <Route path="/settings"  element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default App
