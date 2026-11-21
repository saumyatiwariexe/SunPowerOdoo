import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import PublicFrame from './PublicFrame'
import { State, useRecord } from '../../app/records'
import { formatPaise } from '../../app/api'

export default function LandingPage() {
  const packages = useRecord('/public/packages')
  const [type, setType] = useState('ON_GRID')
  const systems = (packages.data || []).filter((p) => p.system_type === type)
  return (
    <PublicFrame>
      <section className="public-hero">
        <div className="hero-copy">
          <h1>
            Solar power for
            <br />
            <em>your rooftop.</em>
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
        </div>
        <figure className="hero-image">
          <img
            src="/solar-array.jpg"
            alt="Blue solar panels collecting sunlight outdoors"
            fetchpriority="high"
          />
        </figure>
      </section>
      <section id="packages" className="public-packages">
        <div className="section-line">
          <h2>Solar packages</h2>
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
                    {p.capacity_kw} <small>kW</small>
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
