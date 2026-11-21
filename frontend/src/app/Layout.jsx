import React from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import { modules } from './modules.js'
import Sidebar from './Sidebar.jsx'
import AppIcon from './AppIcon.jsx'
import './shell.css'

export default function Layout() {
  const { pathname } = useLocation()
  const { currentUser, logout } = useAuth()
  const navigate = useNavigate()
  const atHome = pathname === '/workspace'
  const active = modules.find(app => app.path === '/' + pathname.split('/')[1])
  const identity = currentUser.name || currentUser.email
  const signOut = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="sp-shell">
      <a className="sp-skip" href="#workspace-content">Skip to content</a>
      <header className="sp-bar no-print">
        <Link to="/workspace" className="sp-brand" aria-label="SunPower applications">
          <AppIcon name="apps" /><strong>SunPower</strong>
        </Link>
        <span className="sp-location">{atHome ? 'Applications' : active?.label}</span>
        <div className="sp-account">
          <span className="sp-avatar" aria-hidden="true">{identity?.slice(0, 1).toUpperCase()}</span>
          <div className="sp-identity"><strong>{identity}</strong><span>{currentUser.role.toLowerCase()}</span></div>
          <button type="button" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <div className="sp-body">
        {!atHome && <Sidebar />}
        <main id="workspace-content" tabIndex={-1} className={atHome ? 'sp-home' : 'sp-content'}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
