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
      <section className="public-explainer" aria-labelledby="system-title">
        <div className="section-line">
          <div>
            <h2 id="system-title">Which system suits your home?</h2>
            <p className="section-help">Your roof, electricity use and connection determine the right setup. A site survey helps us confirm the details before quoting.</p>
          </div>
        </div>
        <div className="system-comparison">
          <article>
            <AppIcon name="leaf" size={30} />
            <h3>On-grid</h3>
            <p>Solar panels work alongside your electricity connection. A good starting point when grid power is available and you want to offset daytime usage.</p>
            <Link className="text-link" to="/enquiry?type=ON_GRID">Ask about on-grid systems →</Link>
          </article>
          <article>
            <AppIcon name="survey" size={30} />
            <h3>Off-grid</h3>
            <p>A system with battery storage for places that need power beyond the grid connection. Battery size and equipment depend on the loads you need to run.</p>
            <Link className="text-link" to="/enquiry?type=OFF_GRID">Ask about off-grid systems →</Link>
          </article>
        </div>
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
        <p className="package-context">Prices shown are package starting points. Your final quote follows a roof survey and lists the equipment and installation work for your site.</p>
      </section>
      <section className="public-aftercare" aria-labelledby="aftercare-title">
        <div>
          <h2 id="aftercare-title">From the first call to support after installation.</h2>
          <p>We keep your project details together so the team can follow each handoff.</p>
          <Link className="button primary" to="/enquiry">Start an enquiry →</Link>
        </div>
        <ul>
          <li><strong>Roof check before quoting</strong><span>A surveyor records the roof direction, tilt, available area and cable route.</span></li>
          <li><strong>Clear equipment list</strong><span>Your quote shows the selected system and the parts required for it.</span></li>
          <li><strong>Installation record</strong><span>The crew records site photos, system size, test completion and your acceptance.</span></li>
          <li><strong>Serial-based service</strong><span>Delivered equipment is recorded by serial number so support can check its warranty later.</span></li>
        </ul>
      </section>
      <section className="subsidy-note">
        <div>
          <h2>Planning to apply for a subsidy?</h2>
          <p>Tell us when you enquire. The team can track the paperwork alongside your installation. Eligibility and approval depend on the applicable scheme.</p>
        </div>
        <Link className="button" to="/enquiry?subsidy=true">
          Ask about subsidies ↗
        </Link>
      </section>
      <section className="public-faq" aria-labelledby="faq-title">
        <div>
          <h2 id="faq-title">Before you enquire</h2>
          <p>A few details help us prepare for the first conversation.</p>
        </div>
        <div>
          <details><summary>Do I need to know my roof measurements?</summary><p>No. Share your address, approximate system size if you have one, and a contact number. The team can assess the roof during the survey.</p></details>
          <details><summary>When will I receive a final quote?</summary><p>After the roof survey is reviewed and approved, Sales can prepare a quote with the package and itemised parts.</p></details>
          <details><summary>What happens after installation?</summary><p>Delivery records start the equipment warranties. You can contact support with a serial number or phone number if you need service.</p></details>
        </div>
      </section>
    </PublicFrame>
  )
}
