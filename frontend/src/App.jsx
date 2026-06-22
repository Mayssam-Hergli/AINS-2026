import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import DiagnosticPage from './pages/DiagnosticPage'
import ScoresPage from './pages/ScoresPage'
import RoadmapPage from './pages/RoadmapPage'
import AssistantPage from './pages/AssistantPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/profiles/:profileId/diagnostic" element={<DiagnosticPage />} />
          <Route path="/profiles/:profileId/scores" element={<ScoresPage />} />
          <Route path="/profiles/:profileId/roadmap" element={<RoadmapPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
