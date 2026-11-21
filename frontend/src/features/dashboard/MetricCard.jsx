import React from 'react'
import { formatPaise } from '../../app/api.js'

export default function MetricCard({ label, value, type = 'money', trend, icon }) {
  const formatted = type === 'money' ? formatPaise(value ?? 0)
                  : type === 'count' ? (value ?? 0).toLocaleString('en-IN')
                  : value ?? '—'

  const trendColor = trend > 0 ? 'text-emerald-600' : trend < 0 ? 'text-red-500' : 'text-slate-400'
  const trendIcon  = trend > 0 ? '↑' : trend < 0 ? '↓' : '—'

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        {icon && <span className="text-xl">{icon}</span>}
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-900 truncate">{formatted}</p>
      {trend !== undefined && (
        <p className={`mt-1 text-xs font-medium ${trendColor}`}>
          {trendIcon} {Math.abs(trend)}% from last period
        </p>
      )}
    </div>
  )
}
