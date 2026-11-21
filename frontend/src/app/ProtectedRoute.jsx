import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import Spinner from './components/Spinner.jsx'
import { hasRole, homeFor } from './navigation'

export default function ProtectedRoute({ children, roles }) {
  const { currentUser, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!currentUser) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && !roles.some((role) => hasRole(currentUser, role))) {
    return <Navigate to={homeFor(currentUser.role)} replace />
  }

  return children
}
