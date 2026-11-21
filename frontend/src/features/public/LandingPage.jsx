import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import PublicFrame from './PublicFrame'
import { State, useRecord } from '../../app/records'
import { formatPaise } from '../../app/api'
import AppIcon from '../../app/AppIcon'

export default function LandingPage() {
  const packages = useRecord('/public/packages')
  const [type, setType] = useState('ON_GRID')
  const systems = (packages.data || []).filter((p) => p.system_type === type)
  return (
    <PublicFrame>
      <section className="public-hero">
        <div className="hero-copy">
          <h1>
            Your roof.
            <br />
            <em>A brighter future.</em>
          </h1>
          <p>
            Explore on-grid and off-grid systems for your home. Our team surveys your roof, installs your
            panels and supports them after switch-on.
          </p>
          <div className="actions">
            <Link className="button primary" to="/enquiry">
              Request a quote <span aria-hidden="true">↗</span>
            </Link>
            <a className="text-link" href="#packages">
              Explore packages ↓
            </a>
          </div>
          <div className="hero-benefits">
            <span><AppIcon name="survey" size={18} />Site-specific planning</span>
            <span><AppIcon name="leaf" size={18} />Support after installation</span>
          </div>
        </div>
        <figure className="hero-image">
          <img
            src="/solar-array.jpg"
            alt="Blue solar panels collecting sunlight outdoors"
            fetchpriority="high"
          />
          <figcaption><AppIcon name="leaf" /><span>Power starts at home.<small>Find the right system for your rooftop.</small></span></figcaption>
        </figure>
      </section>
      <section className="solar-journey" aria-labelledby="journey-title">
        <div><h2 id="journey-title">From your first question<br />to your first solar day.</h2><p>One team through every step.</p></div>
        <ol>
          <li><AppIcon name="people" size={28} /><strong>Tell us about your roof</strong><p>Share your location and power needs.</p></li>
          <li><AppIcon name="survey" size={28} /><strong>Get a site survey</strong><p>We check your roof before preparing a quote.</p></li>
          <li><AppIcon name="calendar" size={28} /><strong>Install &amp; switch on</strong><p>Your crew fits and tests the system.</p></li>
        </ol>
      </section>
      <section id="packages" className="public-packages">
        <div className="section-line">
          <div><h2>Find your solar fit.</h2><p className="section-help">Choose a system and explore available capacities.</p></div>
          <div className="switcher">
            {[
              ['ON_GRID', 'On-grid'],
              ['OFF_GRID', 'Off-grid'],
            ].map(([key, label]) => (
              <button aria-pressed={type === key} key={key} onClick={() => setType(key)}>
                {label}
              </button>
            ))}
          </div>
        </div>
        <State resource={packages}>
          {systems.length ? (
            <ul className="package-list">
              {systems.map((p) => (
                <li key={p.id}>
                  <span className="capacity">
                    <AppIcon name="survey" size={32} />{p.capacity_kw} <small>kW</small>
                  </span>
                  <strong>{p.name}</strong>
                  <span>{formatPaise(p.price_paise)}</span>
                  <Link
                    aria-label={'Enquire about ' + p.name}
                    to={'/enquiry?kw=' + p.capacity_kw + '&type=' + type}
                  >
                    Enquire ↗
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="state">
              No packages are listed for this system type.{' '}
              <Link to="/enquiry">Ask about your roof.</Link>
            </p>
          )}
        </State>
      </section>
      <section className="subsidy-note">
        <div>
          <h2>Planning to apply for a subsidy?</h2>
          <p>Include your interest in PM Surya Ghar when you request a quote.</p>
        </div>
        <Link className="button" to="/enquiry?subsidy=true">
          Ask about subsidies ↗
        </Link>
      </section>
    </PublicFrame>
  )
}
