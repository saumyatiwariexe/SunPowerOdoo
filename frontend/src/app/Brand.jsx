import React from 'react'
import { Link } from 'react-router-dom'

export default function Brand({ to = '/' }) {
  return (
    <Link className="brand" aria-label="SunPower home" to={to}>
      <svg width="34" height="32" viewBox="0 0 34 32" aria-hidden="true">
        <g fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round">
          <path d="M3 22h28M8 27h18M9 18a8 8 0 0 1 16 0M17 2v4M5 7l3 3M29 7l-3 3M2 15l4 1M32 15l-4 1" />
        </g>
      </svg>
      <span>SunPower</span>
    </Link>
  )
}
