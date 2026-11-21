import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './AuthContext.jsx'
import ProtectedRoute from './ProtectedRoute.jsx'
import Layout from './Layout.jsx'

// Auth
import LoginPage from '../features/auth/LoginPage.jsx'

// Public
import LandingPage   from '../features/public/LandingPage.jsx'
import EnquiryForm   from '../features/public/EnquiryForm.jsx'
import ThankYouPage  from '../features/public/ThankYouPage.jsx'

// D's features
import LeadsPage       from '../features/leads/LeadsPage.jsx'
import LeadDetailPage  from '../features/leads/LeadDetailPage.jsx'
import DashboardPage   from '../features/dashboard/DashboardPage.jsx'
import SubsidyPage     from '../features/subsidy/SubsidyPage.jsx'

// Placeholder for other teams' features
function Placeholder({ name }) {
  return (
    <div className="flex h-64 items-center justify-center rounded-lg border-2 border-dashed border-slate-300">
      <div className="text-center text-slate-400">
        <div className="text-4xl mb-2">🚧</div>
        <p className="font-medium">{name}</p>
        <p className="text-sm">Coming soon — another team member's module</p>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/"           element={<LandingPage />} />
          <Route path="/enquiry"    element={<EnquiryForm />} />
          <Route path="/thank-you"  element={<ThankYouPage />} />
          <Route path="/login"      element={<LoginPage />} />

          {/* Protected app routes */}
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index path="/dashboard"  element={<ProtectedRoute roles={['DIRECTOR']}><DashboardPage /></ProtectedRoute>} />
            <Route path="/leads"            element={<ProtectedRoute roles={['DIRECTOR','SALES']}><LeadsPage /></ProtectedRoute>} />
            <Route path="/leads/:id"        element={<ProtectedRoute roles={['DIRECTOR','SALES']}><LeadDetailPage /></ProtectedRoute>} />
            <Route path="/subsidy"          element={<ProtectedRoute roles={['DIRECTOR']}><SubsidyPage /></ProtectedRoute>} />

            {/* Placeholders for other teams */}
            <Route path="/catalog"    element={<Placeholder name="Catalog" />} />
            <Route path="/users"      element={<Placeholder name="Users & Roles" />} />
            <Route path="/invoices"   element={<Placeholder name="Invoices" />} />
            <Route path="/quotes"     element={<Placeholder name="Quotes" />} />
            <Route path="/orders"     element={<Placeholder name="Orders" />} />
            <Route path="/surveys"    element={<Placeholder name="Surveys" />} />
            <Route path="/inventory"  element={<Placeholder name="Inventory" />} />
            <Route path="/deliveries" element={<Placeholder name="Deliveries" />} />
            <Route path="/installs"   element={<Placeholder name="Install Jobs" />} />
            <Route path="/tickets"    element={<Placeholder name="Tickets" />} />
            <Route path="/lookup"     element={<Placeholder name="Serial Lookup" />} />

            {/* Default redirect */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
