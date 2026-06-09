import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import CandidateListPage from './pages/CandidateListPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import RegisterPage from './pages/RegisterPage'

function PrivateRoute({ children }) {
  const token = localStorage.getItem('token')
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/candidates" element={
          <PrivateRoute>
            <CandidateListPage />
          </PrivateRoute>
        } />
        <Route path="/candidates/:id" element={
          <PrivateRoute>
            <CandidateDetailPage />
          </PrivateRoute>
        } />
        <Route path="*" element={<Navigate to="/candidates" replace />} />
      </Routes>
    </BrowserRouter>
  )
}