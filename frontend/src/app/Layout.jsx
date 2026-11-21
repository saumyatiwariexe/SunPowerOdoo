import React, { useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import AppIcon from './AppIcon'
import { sections } from './navigation'
import { useAuth } from './AuthContext'

export default function Layout() {
  const menu = useRef(null)
  const { currentUser } = useAuth()
  const { pathname } = useLocation()
  const group = sections.find(([, items]) => items.some(([path]) => path === pathname.split('/')[1]))
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 761px)')
    const closeOnDesktop = () => {
      if (desktop.matches) menu.current?.close()
    }
    desktop.addEventListener('change', closeOnDesktop)
    return () => desktop.removeEventListener('change', closeOnDesktop)
  }, [])
  return (
    <div className="workspace">
      <a href="#workspace-main" className="skip">
        Skip to content
      </a>
      <aside className="rail">
        <Sidebar />
      </aside>
      <dialog
        ref={menu}
        className="mobile-nav"
        aria-label="Navigation"
        onClick={(event) => {
          if (
            event.target === menu.current &&
            event.clientX > menu.current.getBoundingClientRect().right
          )
            menu.current.close()
        }}
      >
        <Sidebar onClose={() => menu.current.close()} />
      </dialog>
      <div className="workspace-body">
        <header className="topline">
          <button
            className="menu-button"
            aria-haspopup="dialog"
            aria-label="Open navigation"
            onClick={() => menu.current.showModal()}
          >
            <AppIcon name="menu" />
          </button>
          <span>Workspace</span>
          <span aria-hidden="true">/</span>
          <strong>{group?.[0] || 'SunPower'}</strong>
          <div className="topline-user">
            <span>{new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(new Date())}</span>
            <span className="avatar" title={currentUser.name}>{currentUser.name?.slice(0, 1)}</span>
          </div>
        </header>
        <main id="workspace-main" className="workspace-main" tabIndex="-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
