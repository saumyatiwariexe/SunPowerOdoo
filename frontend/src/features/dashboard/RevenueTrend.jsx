import React from 'react'
import { api, formatPaise } from '../../app/api'
import { State, useRecord } from '../../app/records'

function buckets(range, invoices) {
  // Use the same India business day as the report API, including on devices abroad.
  const asBusinessDate = (timestamp) => new Date(timestamp + 330 * 60_000)
  const now = asBusinessDate(Date.now())
  const start = new Date(now)
  start.setUTCHours(0, 0, 0, 0)
  if (range === 'week') start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7))
  if (range === 'month') start.setUTCDate(1)
  const groups = new Map()
  const hourly = range === 'today'
  const key = (date) => (hourly ? date.getUTCHours() : date.getUTCDate())
  for (const day = new Date(start); day <= now;) {
    const label = hourly
      ? day.toLocaleTimeString('en-IN', { hour: 'numeric', timeZone: 'UTC' })
      : day.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' })
    groups.set(key(day), { label, amount: 0 })
    if (hourly) day.setUTCHours(day.getUTCHours() + 1)
    else day.setUTCDate(day.getUTCDate() + 1)
  }
  for (const invoice of invoices) {
    const date = asBusinessDate(Date.parse(invoice.issued_at))
    if (date >= start && date <= now) groups.get(key(date)).amount += invoice.total_paise
  }
  return [...groups.values()]
}
async function loadInvoices(path) {
  const rows = []
  for (let page = 1; ; page += 1) {
    const { data, meta } = await api.get(path, { page, page_size: 100 })
    rows.push(...data)
    if (!data.length || rows.length >= meta.total) return { data: rows }
  }
}

export default function RevenueTrend({ range }) {
  const invoices = useRecord('/invoices', loadInvoices)
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
