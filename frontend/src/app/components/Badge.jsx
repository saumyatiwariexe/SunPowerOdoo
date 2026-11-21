import React from 'react'

const VARIANTS = {
  success: 'bg-emerald-100 text-emerald-800',
  warning: 'bg-amber-100 text-amber-800',
  danger:  'bg-red-100 text-red-800',
  info:    'bg-teal-100 text-teal-700',
  neutral: 'bg-slate-100 text-slate-700',
}

export default function Badge({ variant = 'neutral', label, className = '' }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${VARIANTS[variant] ?? VARIANTS.neutral} ${className}`}
    >
      {label}
    </span>
  )
}
