import React from 'react'
import { formatPaise } from '../../app/api.js'
import Spinner from '../../app/components/Spinner.jsx'
import EmptyState from '../../app/components/EmptyState.jsx'

export default function TechHoursTable({ data, loading, error, onRetry }) {
  if (loading) return <div className="flex justify-center py-6"><Spinner /></div>
  if (error) return (
    <div className="text-center py-6">
      <p className="text-sm text-red-500 mb-2">{error}</p>
      {onRetry && <button onClick={onRetry} className="text-sm text-amber-600 hover:underline">Retry</button>}
    </div>
  )
  if (!data?.length) return <EmptyState title="No technician data" icon="👷" description="No completed jobs this month." />

  const totHours = data.reduce((s, r) => s + (r.total_hours ?? 0), 0)
  const totAmount = data.reduce((s, r) => s + (r.amount_due_paise ?? 0), 0)

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            {['Technician', 'Hours Worked', 'Rate / hr', 'Amount Due'].map(h => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {data.map((row, i) => (
            <tr key={row.user_id ?? i}>
              <td className="px-4 py-3 text-sm font-medium text-slate-800">{row.name || '—'}</td>
              <td className="px-4 py-3 text-sm text-slate-700">{(row.total_hours ?? 0).toFixed(1)} h</td>
              <td className="px-4 py-3 text-sm text-slate-700">{formatPaise(row.hourly_rate_paise ?? 0)}</td>
              <td className="px-4 py-3 text-sm font-semibold text-slate-900">{formatPaise(row.amount_due_paise ?? 0)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot className="bg-slate-50 font-semibold">
          <tr>
            <td className="px-4 py-3 text-sm text-slate-700">Total</td>
            <td className="px-4 py-3 text-sm text-slate-700">{totHours.toFixed(1)} h</td>
            <td />
            <td className="px-4 py-3 text-sm text-amber-700">{formatPaise(totAmount)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
