import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import PublicFrame from './PublicFrame'
import { State, useRecord } from '../../app/records'
import { formatPaise } from '../../app/api'
import AppIcon from '../../app/AppIcon'

export default function LandingPage() {
  const packages = useRecord('/public/packages')
  const [type, setType] = useState('ON_GRID')
  const [capacity, setCapacity] = useState(3)
  const systems = (packages.data || []).filter((p) => p.system_type === type)
  const selected = systems.find((p) => Number(p.capacity_kw) === capacity) || systems[0]
  return (
    <PublicFrame>
      <section className="public-hero">
        <div className="hero-copy">
          <h1>
            Solar that fits
            <br />
            <em>your real life.</em>
          </h1>
          <p>
            Compare real 1–5 kW packages, see what goes into each system, and start with a plan shaped around your roof and electricity needs.
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
            <span><AppIcon name="survey" size={18} />1–5 kW plans</span>
            <span><AppIcon name="leaf" size={18} />Survey to service</span>
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
      <section id="process" className="solar-journey" aria-labelledby="journey-title">
        <div><h2 id="journey-title">From your first question<br />to your first solar day.</h2><p>One team through every step.</p></div>
        <ol>
          <li><AppIcon name="people" size={28} /><strong>Tell us about your roof</strong><p>Share your location and power needs.</p></li>
          <li><AppIcon name="survey" size={28} /><strong>Get a site survey</strong><p>We check your roof before preparing a quote.</p></li>
          <li><AppIcon name="calendar" size={28} /><strong>Install &amp; switch on</strong><p>Your crew fits and tests the system.</p></li>
        </ol>
      </section>
      <section id="systems" className="public-explainer" aria-labelledby="system-title">
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
          <div><h2>Explore the plans.</h2><p className="section-help">Choose how your system connects, then compare live catalog prices by capacity.</p></div>
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
            <div className="plan-studio">
              <div className="plan-chooser">
                <h3>Pick a capacity to explore</h3>
                <p>Choose from the available 1–5 kW packages. Your electricity bill and roof survey help the team confirm a suitable size.</p>
                <div className="plan-capacities" role="group" aria-label="System capacity">
                  {systems.map((p) => <button type="button" key={p.id} aria-pressed={capacity === Number(p.capacity_kw)}
                    onClick={() => setCapacity(Number(p.capacity_kw))}>{p.capacity_kw} <small>kW</small></button>)}
                </div>
                <p className="plan-chooser-note">Exploring a plan does not place an order.</p>
              </div>
              <article className="plan-feature" aria-live="polite">
                <div className="plan-feature-top"><span>{type === 'ON_GRID' ? 'Grid-connected' : 'Battery-backed'}</span><span>{selected.capacity_kw} kW package</span></div>
                <h3>{selected.name}</h3>
                <p>{type === 'ON_GRID' ? 'Designed around panel generation and your existing grid connection.' : 'Adds battery storage for power needs beyond the grid connection.'}</p>
                <div className="plan-price"><small>Catalog package price</small><strong>{formatPaise(selected.price_paise)}</strong></div>
                <ul>
                  <li>Solar panels and mounting stands</li>
                  <li>Inverter, controller, wiring and safety equipment</li>
                  {type === 'OFF_GRID' && <li>Battery units sized for this package</li>}
                  <li>Installation service line</li>
                </ul>
                <Link className="button primary" to={'/enquiry?kw=' + selected.capacity_kw + '&type=' + type}>Enquire about this plan →</Link>
              </article>
            </div>
          ) : (
            <p className="state">
              No packages are listed for this system type.{' '}
              <Link to="/enquiry">Ask about your roof.</Link>
            </p>
          )}
        </State>
        <p className="package-context">Catalog prices are indicative. The approved survey, chosen components, quantities and any applicable subsidy appear in the final quote. Generation and bill savings depend on the site and usage.</p>
      </section>
      <section className="public-components" aria-labelledby="components-title">
        <div><h2 id="components-title">More than panels on a roof.</h2><p>Generation, conversion, protection and installation work together. Your quote itemises the parts so you can see what is included.</p></div>
        <div className="component-map">
          <div><span>01</span><strong>Panels &amp; structure</strong><p>Modules, stands and connectors form a planned array for your available roof.</p></div>
          <div><span>02</span><strong>Power equipment</strong><p>Inverter, controller, wiring and safety components complete the electrical system.</p></div>
          <div><span>03</span><strong>Storage when needed</strong><p>Off-grid packages add batteries. The survey and quote confirm the configuration.</p></div>
          <div><span>04</span><strong>Installation &amp; handover</strong><p>System packages include an installation service line and documented handover.</p></div>
        </div>
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
      <section id="faq" className="public-faq" aria-labelledby="faq-title">
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
