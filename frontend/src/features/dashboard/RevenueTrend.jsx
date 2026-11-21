import React from 'react'
import { formatPaise } from '../../app/api'
import { State, useRecord } from '../../app/records'

function buckets(range, invoices) {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  if (range === 'week') start.setDate(start.getDate() - ((start.getDay() + 6) % 7))
  if (range === 'month') start.setDate(1)
  const groups = new Map()
  const hourly = range === 'today'
  const key = (date) => (hourly ? date.getHours() : date.toLocaleDateString('en-IN'))
  for (const day = new Date(start); day <= now;) {
    const label = hourly
      ? day.toLocaleTimeString('en-IN', { hour: 'numeric' })
      : day.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
    groups.set(key(day), { label, amount: 0 })
    if (hourly) day.setHours(day.getHours() + 1)
    else day.setDate(day.getDate() + 1)
  }
  for (const invoice of invoices) {
    const date = new Date(invoice.issued_at)
    if (date >= start && date <= now) groups.get(key(date)).amount += invoice.total_paise
  }
  return [...groups.values()]
}
export default function RevenueTrend({ range }) {
  const invoices = useRecord('/invoices')
  const series = buckets(range, invoices.data || [])
  const max = Math.max(0, ...series.map((b) => b.amount))
  return (
    <section className="trend">
      <h2>Invoiced revenue</h2>
      <State resource={invoices}>
        {max ? (
          <>
            <div className="bars" aria-label="Invoiced revenue over time">
              {series.map((b) => (
                <div
                  key={b.label}
                  className="bar-slot"
                  tabIndex="0"
                  aria-label={b.label + ', ' + formatPaise(b.amount)}
                >
                  <span className="bar-value">
                    {b.label} · {formatPaise(b.amount)}
                  </span>
                  <i style={{ height: (b.amount / max) * 100 + '%' }} />
                </div>
              ))}
            </div>
            <div className="axis">
              <span>{series[0].label}</span>
              <span>{series.at(-1).label}</span>
            </div>
          </>
        ) : (
          <p className="trend-empty">No invoiced revenue in this period.</p>
        )}
      </State>
    </section>
  )
}
