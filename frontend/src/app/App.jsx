import React, { Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext.jsx'
import ProtectedRoute from './ProtectedRoute.jsx'
import Layout from './Layout.jsx'
import Workspace from './Workspace.jsx'
import { featurePage, modules } from './modules.js'
import ToastContainer from './components/Toast.jsx'
import Spinner from './components/Spinner.jsx'
import LoginPage from '../features/auth/LoginPage.jsx'
import LandingPage from '../features/public/LandingPage.jsx'
import EnquiryForm from '../features/public/EnquiryForm.jsx'
import ThankYouPage from '../features/public/ThankYouPage.jsx'

const LeadDetail = featurePage('leads/LeadDetail')

function ModuleRoute({ roles, Page }) {
  const { currentUser } = useAuth()
  if (!Page || !roles.includes(currentUser.role)) return <Navigate to="/workspace" replace />
  return <Suspense fallback={<div role="status" aria-label="Loading page" className="p-6"><Spinner /></div>}><Page /></Suspense>
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/enquiry" element={<EnquiryForm />} />
          <Route path="/thank-you" element={<ThankYouPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/workspace" element={<Workspace />} />
            {modules.map(({ path, roles, Page }) => (
              <Route key={path} path={path} element={<ModuleRoute roles={roles} Page={Page} />} />
            ))}
            <Route path="/leads/:id" element={<ModuleRoute roles={['DIRECTOR', 'SALES']} Page={LeadDetail} />} />
            <Route path="*" element={<Navigate to="/workspace" replace />} />
          </Route>
        </Routes>
        <ToastContainer />
      </AuthProvider>
    </BrowserRouter>
  )
}
