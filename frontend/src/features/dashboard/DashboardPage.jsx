import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import RevenueTrend from './RevenueTrend'
import { api, formatPaise } from '../../app/api'
import { DataTable, Heading, State, useRecord } from '../../app/records'
import AppIcon from '../../app/AppIcon'

export default function DashboardPage() {
  const [range, setRange] = useState('today')
  const [month, setMonth] = useState('')
  const [report, setReport] = useState('Profit per job')
  const [error, setError] = useState('')
  const summary = useRecord('/reports/summary?range=' + range)
  const unfinished = useRecord('/reports/unfinished')
  const [sort, setSort] = useState('desc')
  const profitQuery = new URLSearchParams({ range, sort })
  const profit = useRecord('/reports/profit-per-job?' + profitQuery)
  const hours = useRecord('/reports/technician-hours' + (month ? '?month=' + month : ''))
  async function download() {
    try {
      setError('')
      const hoursSelected = report === 'Technician hours'
      const query = hoursSelected ? new URLSearchParams({ report: 'hours' }) : profitQuery
      if (hoursSelected && month) query.set('month', month)
      const file = await api.getRaw('/reports/export.csv?' + query)
      const url = URL.createObjectURL(await file.blob())
      const a = document.createElement('a')
      a.href = url
      a.download = hoursSelected ? 'sunpower-hours.csv' : 'sunpower-profit.csv'
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setError(err.message)
    }
  }
  return (
    <>
      <Heading title="Operations overview">
        <button className="button" onClick={() => window.print()}>
          Print
        </button>
        <button className="button primary" onClick={download}>
          Export CSV ↓
        </button>
      </Heading>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="view-tabs">
        {[
          ['today', 'Today'],
          ['week', 'This week'],
          ['month', 'This month'],
        ].map(([key, name]) => (
          <button key={key} aria-pressed={range === key} onClick={() => setRange(key)}>
            {name}
          </button>
        ))}
      </div>
      <State resource={summary}>
        {summary.data && (
          <>
            <dl className="financials">
              {[
                ['revenue_paise', 'Revenue'],
                ['collected_paise', 'Collected'],
                ['outstanding_paise', 'Outstanding'],
              ].map(([k, name]) => (
                <div key={k}>
                  <dt><AppIcon name={k === 'outstanding_paise' ? 'document' : 'chart'} />{name}</dt>
                  <dd>{formatPaise(summary.data[k])}</dd>
                </div>
              ))}
            </dl>
            <RevenueTrend range={range} />
            <div className="dashboard-split">
              <section>
                <h2>Work in progress</h2>
                <p className="section-help">Select a stage to move the next job forward.</p>
                <State resource={unfinished}>
                  {unfinished.data && (
                    <ul className="work-rows">
                      {[
                        ['awaiting_survey', 'Awaiting survey', 'surveys'],
                        ['awaiting_payment', 'Awaiting payment', 'orders'],
                        ['awaiting_dispatch', 'Awaiting dispatch', 'deliveries'],
                        ['awaiting_install', 'Awaiting installation', 'installs'],
                      ].map(([k, name, path]) => (
                        <li key={k}>
                          <Link to={'/' + path}>
                            <AppIcon name={{ surveys: 'survey', orders: 'bag', deliveries: 'truck', installs: 'calendar' }[path]} />
                            <span className="stage-label">{name}<span className="stage-track"><span style={{ width: (unfinished.data[k] / Math.max(1, ...Object.values(unfinished.data))) * 100 + '%' }} /></span></span>
                            <strong>{unfinished.data[k]}</strong><span aria-hidden="true">↗</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </State>
              </section>
              <section>
                <h2>Field &amp; service</h2>
                <ul className="work-rows">
                  {[
                    ['jobs_completed', 'Completed installations', 'installs'],
                    ['jobs_unfinished', 'Unfinished installations', 'installs'],
                    ['open_tickets', 'Open tickets', 'tickets'],
                    ['low_stock_count', 'Low stock items', 'inventory'],
                  ].map(([k, name, path]) => (
                    <li key={k}>
                      <Link to={'/' + path}>
                        {name}
                        <strong>{summary.data[k]}</strong>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            </div>
          </>
        )}
      </State>
      <div className="section-line">
        <h2>Reports</h2>
        <div className="switcher">
          {['Profit per job', 'Technician hours'].map((x) => (
            <button key={x} aria-pressed={report === x} onClick={() => setReport(x)}>
              {x}
            </button>
          ))}
        </div>
      </div>
      {report === 'Profit per job' ? (
        <State resource={profit}>
          <p>Lifetime totals for jobs confirmed, dispatched, invoiced or completed in the selected period.</p>
          <DataTable
            rows={profit.data}
            empty="No job profit to report."
            columns={[
              ['order_number', 'Order'],
              ['customer_name', 'Customer'],
              ['revenue_paise', 'Revenue'],
              ['parts_paise', 'Parts'],
              ['labour_paise', 'Labour'],
              [
                'profit_paise',
                <button onClick={() => setSort(sort === 'desc' ? 'asc' : 'desc')}>
                  Profit {sort === 'desc' ? '↓' : '↑'}
                </button>,
              ],
            ]}
          />
        </State>
      ) : (
        <>
          <label className="tools">
            Report month <input type="month" value={month} onChange={(e) => setMonth(e.target.value)} />
          </label>
          <State resource={hours}>
            <DataTable
              rows={hours.data}
              empty="No technician hours for this month."
              columns={[
                ['name', 'Technician'],
                ['hours_worked', 'Hours'],
                ['hourly_rate_paise', 'Hourly rate'],
                ['amount_due_paise', 'Amount due'],
              ]}
            />
          </State>
        </>
      )}
    </>
  )
}
