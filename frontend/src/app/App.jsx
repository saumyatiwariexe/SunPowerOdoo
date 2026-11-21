import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import { homeFor, sections } from './navigation'
import ProtectedRoute from './ProtectedRoute'
import Layout from './Layout'
import { ToastContainer } from './components/Toast'
import LandingPage from '../features/public/LandingPage'
import EnquiryForm from '../features/public/EnquiryForm'
import ThankYouPage from '../features/public/ThankYouPage'
import ProfilePage from '../features/auth/ProfilePage'
import LoginPage from '../features/auth/LoginPage'
import DashboardPage from '../features/dashboard/DashboardPage'
import LeadsPage from '../features/leads/LeadsPage'
import LeadDetailPage from '../features/leads/LeadDetailPage'
import { SurveysPage, SurveyDetail } from '../features/surveys/SurveysPage'
import { InstallsPage, InstallDetail } from '../features/installs/InstallsPage'
import { QuotesPage, QuoteDetail } from '../features/quotes/QuotesPage'
import { OrdersPage, OrderDetail } from '../features/orders/OrdersPage'
import { CatalogPage, PackageDetail } from '../features/catalog/CatalogPage'
import { SubsidyPage, SubsidyDetail } from '../features/subsidy/SubsidyPage'
import { DeliveriesPage, DeliveryDetail } from '../features/deliveries/DeliveriesPage'
import InventoryPage from '../features/inventory/InventoryPage'
import { InvoicesPage, InvoiceDetail } from '../features/invoices/InvoicesPage'
import TicketBoard from '../features/tickets/TicketBoard'
import LookupPage from '../features/lookup/LookupPage'

const pages = {
  dashboard: [DashboardPage],
  leads: [LeadsPage, LeadDetailPage],
  surveys: [SurveysPage, SurveyDetail],
  installs: [InstallsPage, InstallDetail],
  quotes: [QuotesPage, QuoteDetail],
  orders: [OrdersPage, OrderDetail],
  catalog: [CatalogPage, PackageDetail],
  subsidy: [SubsidyPage, SubsidyDetail],
  inventory: [InventoryPage],
  deliveries: [DeliveriesPage, DeliveryDetail],
  invoices: [InvoicesPage, InvoiceDetail],
  tickets: [TicketBoard],
  lookup: [LookupPage],
}
function WorkspaceHome() {
  const { currentUser } = useAuth()
  return <Navigate to={homeFor(currentUser.role)} replace />
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
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            {sections.flatMap(([, items]) =>
              items.flatMap(([path, , , roles]) =>
                pages[path].map((Page, i) => {
                  const url = '/' + path + (i ? '/:id' : '')
                  return (
                    <Route
                      key={url}
                      path={url}
                      element={
                        <ProtectedRoute roles={roles}>
                          <Page />
                        </ProtectedRoute>
                      }
                    />
                  )
                }),
              ),
            )}
            <Route path="/users" element={<ProfilePage />} />
            <Route path="*" element={<WorkspaceHome />} />
          </Route>
        </Routes>
        <ToastContainer />
      </AuthProvider>
    </BrowserRouter>
  )
}
