import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import { modules } from './modules.js'
import AppIcon from './AppIcon.jsx'

export default function Sidebar() {
  const { currentUser } = useAuth()
  return (
    <aside className="sp-sidebar no-print">
      <nav aria-label="Applications">
        <NavLink to="/workspace"><AppIcon name="apps" />All applications</NavLink>
        {modules.filter(app => app.Page && app.roles.includes(currentUser.role)).map(app => (
          <NavLink key={app.path} to={app.path}>
            <span style={{ color: app.color }}><AppIcon name={app.icon} /></span>{app.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
