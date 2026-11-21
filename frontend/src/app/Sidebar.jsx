import React from 'react'
import { Link, NavLink } from 'react-router-dom'
import Brand from './Brand'
import AppIcon from './AppIcon'
import { useAuth } from './AuthContext'
import { homeFor, sections, human } from './navigation'

export default function Sidebar({ onClose }) {
  const { currentUser: user, logout } = useAuth()
  return (
    <div className="sidebar">
      <div className="sidebar-head">
        <Brand to={homeFor(user.role)} />
        <button className="menu-button" aria-label="Close navigation" onClick={onClose}>
          ×
        </button>
      </div>
      <nav aria-label="Workspace navigation">
        {sections.map(([label, items]) => {
          const visible = items.filter(([, , , roles]) => roles.includes(user.role))
          return (
            visible.length > 0 && (
              <section key={label}>
                <h2>{label}</h2>
                {visible.map(([path, name, icon]) => (
                  <NavLink key={path} to={'/' + path} onClick={onClose}>
                    <AppIcon size={17} name={icon} />
                    {name}
                  </NavLink>
                ))}
              </section>
            )
          )
        })}
      </nav>
      <div className="identity">
        <span className="avatar">{(user.name || user.email).slice(0, 1).toUpperCase()}</span>
        <div>
          <Link to="/users" onClick={onClose} title="Staff profile">
            <strong>{user.name || user.email}</strong>
          </Link>
          <small>{human(user.role)}</small>
        </div>
        <button onClick={logout} aria-label="Sign out" title="Sign out">
          <AppIcon name="exit" size={18} />
        </button>
      </div>
    </div>
  )
}
