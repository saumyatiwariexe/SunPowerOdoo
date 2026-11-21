import React from 'react'
import { Link } from 'react-router-dom'
import Brand from '../../app/Brand'

export default function PublicFrame({ children }) {
  return (
    <div className="public-site">
      <header className="public-head">
        <Brand />
        <nav aria-label="Public navigation">
          <a className="public-nav-systems" href="/#systems">Systems</a>
          <a href="/#packages"><span className="public-nav-wide">Packages</span><span className="public-nav-short">Plans</span></a>
          <Link className="button" to="/customer">My solar</Link>
          <Link className="button public-nav-staff" to="/login">
            <span className="public-nav-wide">Staff sign in</span><span className="public-nav-short">Sign in</span> <span aria-hidden="true">↗</span>
          </Link>
        </nav>
      </header>
      <main>{children}</main>
      <footer className="public-foot">
        <div className="footer-main">
          <div className="footer-intro">
            <Brand />
            <p>Solar plans shaped around your roof, with one team for surveys, installation and service.</p>
            <Link className="button primary" to="/enquiry">Start your enquiry →</Link>
          </div>
          <nav aria-label="Explore SunPower">
            <h2>Explore</h2>
            <a href="/#systems">System types</a>
            <a href="/#packages">Plans &amp; prices</a>
            <a href="/#process">How it works</a>
          </nav>
          <nav aria-label="Help and access">
            <h2>Here to help</h2>
            <a href="/#faq">Common questions</a>
            <Link to="/enquiry?subsidy=true">Subsidy enquiry</Link>
            <Link to="/login">Staff sign in</Link>
          </nav>
        </div>
        <div className="footer-bottom"><span>© {new Date().getFullYear()} SunPower Solutions</span><span>Solar installation &amp; service</span></div>
      </footer>
    </div>
  )
}
