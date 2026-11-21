import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'

const NAV = {
  DIRECTOR: [
    { to: '/dashboard',  label: 'Dashboard',  icon: '📊' },
    { to: '/leads',      label: 'Leads',       icon: '📋' },
    { to: '/subsidy',    label: 'Subsidy',     icon: '💰' },
    { to: '/catalog',    label: 'Catalog',     icon: '📦', placeholder: true },
    { to: '/users',      label: 'Users',       icon: '👥', placeholder: true },
    { to: '/invoices',   label: 'Invoices',    icon: '🧾', placeholder: true },
  ],
  SALES: [
    { to: '/leads',      label: 'Leads',       icon: '📋' },
    { to: '/quotes',     label: 'Quotes',      icon: '📄', placeholder: true },
    { to: '/orders',     label: 'Orders',      icon: '🛒', placeholder: true },
  ],
  SURVEYOR: [
    { to: '/surveys',    label: 'Surveys',     icon: '🏠', placeholder: true },
  ],
  WAREHOUSE: [
    { to: '/inventory',  label: 'Inventory',   icon: '📦', placeholder: true },
    { to: '/deliveries', label: 'Deliveries',  icon: '🚚', placeholder: true },
  ],
  CREW: [
    { to: '/installs',   label: 'My Jobs',     icon: '🔧', placeholder: true },
  ],
  SUPPORT: [
    { to: '/tickets',    label: 'Tickets',     icon: '🎫', placeholder: true },
    { to: '/lookup',     label: 'Lookup',      icon: '🔍', placeholder: true },
  ],
}

export default function Sidebar({ onClose }) {
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()
  const links = NAV[currentUser?.role] || []

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="sidebar flex h-full flex-col bg-slate-900 text-slate-100">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-700">
        <span className="text-2xl">☀️</span>
        <span className="text-lg font-bold text-amber-400">SunPower</span>
        {onClose && (
          <button
            onClick={onClose}
            className="ml-auto text-slate-400 hover:text-white lg:hidden"
            aria-label="Close menu"
          >
            ✕
          </button>
        )}
      </div>

      {/* Nav links */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {links.map(({ to, label, icon, placeholder }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg mb-1 text-sm transition-colors
              ${placeholder
                ? 'text-slate-500 cursor-default pointer-events-none'
                : isActive
                  ? 'bg-amber-500 text-slate-900 font-semibold'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            <span>{label}</span>
            {placeholder && (
              <span className="ml-auto text-xs text-slate-600 italic">soon</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* User info + logout */}
      <div className="border-t border-slate-700 px-4 py-3">
        <div className="text-xs text-slate-400 mb-1 truncate">{currentUser?.email}</div>
        <div className="text-xs text-amber-400 font-medium mb-3">{currentUser?.role}</div>
        <button
          onClick={handleLogout}
          className="w-full text-left text-sm text-slate-400 hover:text-white transition-colors"
        >
          Sign out →
        </button>
      </div>
    </div>
  )
}
