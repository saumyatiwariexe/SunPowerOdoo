import React, { useState } from 'react'
import { formatPaise } from '../../app/api.js'
import Spinner from '../../app/components/Spinner.jsx'
import EmptyState from '../../app/components/EmptyState.jsx'

export default function ProfitTable({ data = [], loading, error, onRetry }) {
  const [sortKey, setSortKey] = useState('profit_paise')
  const [sortAsc, setSortAsc] = useState(false)

  if (loading) return <div className="flex justify-center py-10"><Spinner /></div>
  if (error) return (
    <div className="text-center py-8">
      <p className="text-sm text-slate-500 mb-3">{error}</p>
      {onRetry && <button onClick={onRetry} className="rounded-lg bg-amber-500 px-4 py-2 text-sm text-white hover:bg-amber-600">Retry</button>}
    </div>
  )
  if (!data.length) return <EmptyState title="No completed jobs yet" icon="📋" />

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey]
    return sortAsc ? (av < bv ? -1 : 1) : (av > bv ? -1 : 1)
  })

  const toggleSort = (key) => {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(false) }
  }

  const Th = ({ k, children }) => (
    <th
      onClick={() => toggleSort(k)}
      className="cursor-pointer select-none px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500 hover:text-slate-800"
    >
      {children} {sortKey === k ? (sortAsc ? '↑' : '↓') : ''}
    </th>
  )

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <Th k="order_number">Order</Th>
            <Th k="customer_name">Customer</Th>
            <Th k="revenue_paise">Revenue</Th>
            <Th k="cost_paise">Cost</Th>
            <Th k="profit_paise">Profit</Th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {sorted.map((row, i) => {
            const profit = row.profit_paise ?? 0
            const isPos  = profit >= 0
            return (
              <tr key={row.order_id ?? i} className="hover:bg-slate-50">
                <td className="px-4 py-3 text-sm font-mono text-slate-700">{row.order_number || `#${row.order_id}`}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{row.customer_name || '—'}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{formatPaise(row.revenue_paise)}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{formatPaise(row.cost_paise)}</td>
                <td className={`px-4 py-3 text-sm font-semibold ${isPos ? 'text-emerald-700' : 'text-red-600'}`}>
                  {isPos ? '+' : ''}{formatPaise(profit)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
