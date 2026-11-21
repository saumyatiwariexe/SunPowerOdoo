import React from 'react'
import { Link } from 'react-router-dom'
import Brand from '../../app/Brand'

export default function PublicFrame({ children }) {
  return (
    <div className="public-site">
      <header className="public-head">
        <Brand />
        <nav aria-label="Public navigation">
          <a href="/#packages">Packages</a>
          <Link className="button" to="/login">
            Staff sign in <span aria-hidden="true">↗</span>
          </Link>
        </nav>
      </header>
      <main>{children}</main>
      <footer className="public-foot">
        <Brand />
        <span>Solar installation &amp; service</span>
      </footer>
    </div>
  )
}
