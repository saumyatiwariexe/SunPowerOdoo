import React, { useState } from 'react'
import Spinner from './Spinner.jsx'
import EmptyState from './EmptyState.jsx'

/**
 * Generic sortable table.
 * columns: [{ key, label, render?, sortable?, className? }]
 * data: array of row objects
 */
export default function Table({ columns, data, loading, error, onRetry, emptyTitle = 'No records', emptyDescription, onRowClick }) {
  const [sortKey, setSortKey]   = useState(null)
  const [sortAsc, setSortAsc]   = useState(true)

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center py-12 text-center gap-3">
        <span className="text-4xl">⚠️</span>
        <p className="text-sm text-slate-600">{error}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
          >
            Retry
          </button>
        )}
      </div>
    )
  }

  if (!data || data.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />
  }

  const sorted = sortKey
    ? [...data].sort((a, b) => {
        const av = a[sortKey], bv = b[sortKey]
        if (av === bv) return 0
        const cmp = av < bv ? -1 : 1
        return sortAsc ? cmp : -cmp
      })
    : data

  const handleSort = (key) => {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(true) }
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
                className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500
                  ${col.sortable ? 'cursor-pointer select-none hover:text-slate-800' : ''}
                  ${col.className ?? ''}`}
              >
                {col.label}
                {col.sortable && sortKey === col.key && (
                  <span className="ml-1">{sortAsc ? '↑' : '↓'}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {sorted.map((row, ri) => (
            <tr
              key={row.id ?? ri}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`${onRowClick ? 'cursor-pointer hover:bg-brand-50' : ''} transition-colors`}
            >
              {columns.map(col => (
                <td key={col.key} className={`px-4 py-3 text-sm text-slate-700 ${col.className ?? ''}`}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
