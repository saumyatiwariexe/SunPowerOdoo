import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { DataTable, Heading, Pager, State, useRecord } from '../../app/records'
import { human } from '../../app/navigation'
import NewLeadModal from './NewLeadModal'

const statuses = ['NEW', 'CONTACTED', 'SURVEY_PENDING', 'SURVEY_DONE', 'QUOTED', 'WON', 'LOST']
export default function LeadsPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [sort, setSort] = useState('recent')
  const params = new URLSearchParams({ page })
  if (status) params.set('status', status)
  if (search.trim()) params.set('q', search.trim())
  const leads = useRecord('/leads?' + params)
  useEffect(() => {
    const timer = window.setInterval(leads.reload, 15000)
    return () => window.clearInterval(timer)
  }, [leads.reload])
  const rows = [...(leads.data || [])]
  if (sort === 'status') rows.sort((a, b) => statuses.indexOf(a.status) - statuses.indexOf(b.status))
  return (
    <>
      <Heading title="Lead inbox">
        <button className="button primary" onClick={() => setOpen(true)}>
          ＋ New lead
        </button>
      </Heading>
      <div className="tools">
        <input
          type="search"
          aria-label="Search by name or phone"
          placeholder="Search name or phone"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
        />
        <select
          aria-label="Lead status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All statuses</option>
          {statuses.map((s) => (
            <option value={s} key={s}>
              {human(s)}
            </option>
          ))}
        </select>
        <select aria-label="Sort current page" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="recent">Newest first</option>
          <option value="status">Order page by status</option>
        </select>
      </div>
      <State resource={leads}>
        <DataTable
          rows={rows}
          empty="No leads match this view."
          columns={[
            [
              'customer',
              'Customer',
              (r) => (
                <Link className="text-link" to={'/leads/' + r.id}>
                  {r.customer?.name || 'Customer #' + r.customer_id}
                </Link>
              ),
            ],
            ['phone', 'Phone', (r) => r.customer?.phone],
            ['source', 'Source'],
            ['requested_kw', 'Size (kW)'],
            ['system_type', 'System'],
            ['status', 'Status'],
            ['created_at', 'Received'],
          ]}
        />
        <Pager page={page} setPage={setPage} meta={leads.meta} />
      </State>
      {open && (
        <NewLeadModal onClose={() => setOpen(false)} onCreated={(r) => navigate('/leads/' + r.id)} />
      )}
    </>
  )
}
