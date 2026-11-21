import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function ThankYouPage() {
  const { state } = useLocation()
  const reference = state?.reference

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow p-10 text-center">
        <div className="text-6xl mb-4">🎉</div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Thank You!</h1>
        <p className="text-slate-500 mb-6">
          Your enquiry has been received. Our team will contact you within 24 hours.
        </p>

        {reference && (
          <div className="mb-6 rounded-lg bg-amber-50 border border-amber-200 px-5 py-4">
            <p className="text-xs text-amber-700 font-medium uppercase tracking-wide mb-1">Reference Number</p>
            <p className="text-2xl font-bold text-amber-800">{reference}</p>
            <p className="text-xs text-amber-600 mt-1">Keep this for your records</p>
          </div>
        )}

        <div className="flex flex-col gap-3">
          <Link
            to="/enquiry"
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Submit Another Enquiry
          </Link>
          <Link
            to="/"
            className="rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-semibold text-white hover:bg-amber-600 transition-colors"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  )
}
