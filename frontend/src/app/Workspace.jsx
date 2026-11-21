import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from './AuthContext.jsx'
import { modules } from './modules.js'
import AppIcon from './AppIcon.jsx'

export default function Workspace() {
  const { currentUser } = useAuth()
  const [query, setQuery] = useState('')
  const visible = modules.filter(app => app.roles.includes(currentUser.role)
    && app.label.toLowerCase().includes(query.trim().toLowerCase()))

  return (
    <section className="sp-launcher">
      <div className="sp-launcher-inner">
        <h1>Applications</h1>
        <label className="sp-search">
          <AppIcon name="search" size={19} />
          <input aria-label="Search applications" type="search" placeholder="Search applications" value={query}
            onChange={event => setQuery(event.target.value)} />
        </label>
        <ul className="sp-grid">
          {visible.map(app => {
            const content = <>
              <span className="sp-tile" style={{ '--tile': app.color }}><AppIcon name={app.icon} size={31} /></span>
              <strong>{app.label}</strong>
              {!app.Page && <small>Coming soon</small>}
            </>
            return <li key={app.path}>{app.Page
              ? <Link className="sp-app" to={app.path}>{content}</Link>
              : <span className="sp-app sp-pending">{content}</span>}</li>
          })}
        </ul>
        {!visible.length && <p role="status" className="sp-empty">No matching applications.</p>}
      </div>
    </section>
  )
}
