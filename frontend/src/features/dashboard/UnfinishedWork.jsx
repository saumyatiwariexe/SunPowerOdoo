import React from 'react'
import Spinner from '../../app/components/Spinner.jsx'
import EmptyState from '../../app/components/EmptyState.jsx'

const STAGE_ICONS = {
  awaiting_survey:   '🏠',
  awaiting_payment:  '💳',
  awaiting_dispatch: '🚚',
  awaiting_install:  '🔧',
}

export default function UnfinishedWork({ data, loading, error, onRetry }) {
  if (loading) return <div className="flex justify-center py-6"><Spinner /></div>
  if (error) return (
    <div className="text-center py-6">
      <p className="text-sm text-red-500 mb-2">{error}</p>
      {onRetry && <button onClick={onRetry} className="text-sm text-amber-600 hover:underline">Retry</button>}
    </div>
  )
  if (!data || Object.values(data).every(v => !v?.length)) {
    return <EmptyState title="All caught up!" icon="✅" description="No stuck orders right now." />
  }

  return (
    <div className="space-y-4">
      {Object.entries(data).map(([stage, orders]) => {
        if (!orders?.length) return null
        return (
          <div key={stage} className="rounded-lg border border-amber-100 bg-amber-50 p-4">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-lg">{STAGE_ICONS[stage] || '📋'}</span>
              <h4 className="text-sm font-semibold text-amber-900 capitalize">
                {stage.replace(/_/g, ' ')} ({orders.length})
              </h4>
            </div>
            <div className="space-y-2">
              {orders.map((o, i) => (
                <div key={o.id ?? i} className="flex justify-between text-sm">
                  <span className="font-mono text-amber-800">{o.order_number || `#${o.id}`}</span>
                  <span className="text-amber-700">{o.customer_name}</span>
                  <span className="text-amber-600 text-xs">{o.days_waiting ? `${o.days_waiting}d` : '—'}</span>
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
