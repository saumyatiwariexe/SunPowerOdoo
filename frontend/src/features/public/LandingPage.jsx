import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api.js'
import Spinner from '../../app/components/Spinner.jsx'

const SYSTEM_ICONS = { 'ON_GRID': '⚡', 'OFF_GRID': '🔋' }

export default function LandingPage() {
  const [packages, setPackages] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')

  useEffect(() => {
    api.get('/public/packages')
      .then(({ data }) => setPackages(data || []))
      .catch(() => setError('Could not load packages'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <header className="border-b border-slate-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <span className="text-2xl">☀️</span> SunPower
          </div>
          <Link to="/login" className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 transition-colors">
            Staff Login
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="bg-gradient-to-br from-slate-900 via-slate-800 to-amber-900 text-white py-20 px-4">
        <div className="mx-auto max-w-4xl text-center">
          <div className="text-6xl mb-6">☀️</div>
          <h1 className="text-4xl md:text-5xl font-extrabold leading-tight mb-4">
            Clean Energy for<br />Every Indian Home
          </h1>
          <p className="text-lg text-slate-300 mb-8 max-w-2xl mx-auto">
            Professional rooftop solar installation from 1 kW to 5 kW. On-grid and off-grid systems. 20-year panel warranty. Government subsidy assistance included.
          </p>
          <Link
            to="/enquiry"
            className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-8 py-4 text-lg font-bold text-white hover:bg-amber-400 transition-colors shadow-lg"
          >
            Get Free Quote →
          </Link>
        </div>
      </section>

      {/* Stats strip */}
      <section className="bg-amber-500 text-white py-6">
        <div className="mx-auto max-w-4xl grid grid-cols-2 md:grid-cols-4 gap-4 text-center px-4">
          {[
            { n: '500+', label: 'Installations' },
            { n: '20yr', label: 'Panel Warranty' },
            { n: '24hr', label: 'Support' },
            { n: '₹0', label: 'Hidden Charges' },
          ].map(s => (
            <div key={s.label}>
              <div className="text-2xl font-extrabold">{s.n}</div>
              <div className="text-sm opacity-80">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Packages */}
      <section className="py-16 px-4 bg-slate-50">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-3xl font-bold text-center text-slate-900 mb-2">Our Packages</h2>
          <p className="text-center text-slate-500 mb-10">Choose the right system for your home or business</p>

          {loading && <div className="flex justify-center py-10"><Spinner size="lg" /></div>}
          {error   && <p className="text-center text-red-500">{error}</p>}

          {!loading && !error && packages.length === 0 && (
            <p className="text-center text-slate-400">Packages coming soon.</p>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {packages.map(pkg => (
              <div key={pkg.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 hover:shadow-md transition-shadow">
                <div className="text-2xl mb-3">{SYSTEM_ICONS[pkg.system_type] || '☀️'}</div>
                <h3 className="font-bold text-slate-900 text-lg">{pkg.name}</h3>
                {pkg.capacity_kw && (
                  <p className="text-amber-600 font-semibold mt-1">{pkg.capacity_kw} kW</p>
                )}
                {pkg.system_type && (
                  <span className="inline-block mt-2 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                    {pkg.system_type.replace('_', '-')}
                  </span>
                )}
                {pkg.description && (
                  <p className="mt-3 text-sm text-slate-500">{pkg.description}</p>
                )}
                <Link
                  to={`/enquiry?package=${pkg.id}&kw=${pkg.capacity_kw || ''}&type=${pkg.system_type || ''}`}
                  className="mt-5 block w-full rounded-lg bg-amber-500 py-2 text-center text-sm font-semibold text-white hover:bg-amber-600 transition-colors"
                >
                  Enquire Now
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Subsidy banner */}
      <section className="bg-emerald-50 border-y border-emerald-100 py-10 px-4">
        <div className="mx-auto max-w-3xl text-center">
          <div className="text-3xl mb-3">🏛️</div>
          <h2 className="text-xl font-bold text-emerald-900">Government Subsidy Available</h2>
          <p className="mt-2 text-emerald-700 text-sm">
            Get up to ₹78,000 subsidy under the PM Surya Ghar Muft Bijli Yojana. We handle all the paperwork for you.
          </p>
          <Link to="/enquiry?subsidy=true" className="mt-5 inline-block rounded-lg border border-emerald-600 text-emerald-700 px-5 py-2 text-sm font-semibold hover:bg-emerald-100 transition-colors">
            Learn About Subsidy →
          </Link>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 text-center">
        <h2 className="text-3xl font-bold text-slate-900 mb-4">Ready to go solar?</h2>
        <p className="text-slate-500 mb-8">Fill out a quick enquiry and we'll get back to you within 24 hours.</p>
        <Link
          to="/enquiry"
          className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-8 py-4 text-white font-bold hover:bg-slate-800 transition-colors"
        >
          Start Your Enquiry →
        </Link>
      </section>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 text-sm py-6 px-4 text-center">
        © 2024 SunPower Solar Installations. All rights reserved.
      </footer>
    </div>
  )
}
