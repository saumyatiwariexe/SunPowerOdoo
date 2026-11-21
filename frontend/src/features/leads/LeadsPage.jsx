import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../app/api.js'
import PageHeader from '../../app/components/PageHeader.jsx'
import Badge from '../../app/components/Badge.jsx'
import Table from '../../app/components/Table.jsx'
import EmptyState from '../../app/components/EmptyState.jsx'
import Spinner from '../../app/components/Spinner.jsx'
import NewLeadModal from './NewLeadModal.jsx'
import { toast } from '../../app/components/Toast.jsx'

const SOURCE_BADGE  = { WEB: 'info', WHATSAPP: 'success', CALL: 'warning' }
const STATUS_BADGE  = {
  NEW: 'neutral', CONTACTED: 'info', SURVEY_PENDING: 'warning',
  SURVEY_DONE: 'info', QUOTED: 'info', WON: 'success', LOST: 'danger',
}
const STATUS_OPTS = ['', 'NEW', 'CONTACTED', 'SURVEY_PENDING', 'SURVEY_DONE', 'QUOTED', 'WON', 'LOST']

export default function LeadsPage() {
  const navigate = useNavigate()
  const [leads,   setLeads]   = useState([])
  const [meta,    setMeta]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [status,  setStatus]  = useState('')
  const [q,       setQ]       = useState('')
  const [page,    setPage]    = useState(1)
  const [showNew, setShowNew] = useState(false)
  const intervalRef = useRef(null)

  const fetchLeads = async (silent = false) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const { data, meta } = await api.get('/leads', { status: status || undefined, q: q || undefined, page, page_size: 20 })
      setLeads(data || [])
      setMeta(meta)
    } catch (err) {
      setError(err.message || 'Failed to load leads')
    } finally {
      setLoading(false)
    }
  }

  // Initial fetch and deps change
  useEffect(() => { fetchLeads() }, [status, q, page]) // eslint-disable-line

  // Poll every 15 seconds
  useEffect(() => {
    intervalRef.current = setInterval(() => fetchLeads(true), 15_000)
    return () => clearInterval(intervalRef.current)
  }, [status, q, page]) // eslint-disable-line

  const columns = [
    {
      key: 'source',
      label: 'Source',
      render: (v) => <Badge variant={SOURCE_BADGE[v]} label={v} />,
    },
    {
      key: 'customer',
      label: 'Customer',
      render: (_, row) => (
        <div>
          <div className="font-medium text-slate-900">{row.customer?.name || '—'}</div>
          <div className="text-xs text-slate-400">{row.customer?.phone}</div>
        </div>
      ),
    },
    {
      key: 'requested_kw',
      label: 'Size',
      render: (v) => v ? `${v} kW` : '—',
    },
    {
      key: 'system_type',
      label: 'Type',
      render: (v) => v ? v.replace('_', '-') : '—',
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (v) => <Badge variant={STATUS_BADGE[v]} label={v?.replace('_', ' ')} />,
    },
    {
      key: 'created_at',
      label: 'Created',
      sortable: true,
      render: (v) => v ? new Date(v).toLocaleDateString('en-IN') : '—',
    },
  ]

  return (
    <div>
      <PageHeader
        title="Leads"
        subtitle="All customer enquiries and leads"
        action={
          <button
            onClick={() => setShowNew(true)}
            className="rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 transition-colors"
          >
            + New Lead
          </button>
        }
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <input
          type="search"
          placeholder="Search by name or phone…"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
          value={q}
          onChange={e => { setQ(e.target.value); setPage(1) }}
        />
        <select
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
          value={status}
          onChange={e => { setStatus(e.target.value); setPage(1) }}
        >
          <option value="">All Statuses</option>
          {STATUS_OPTS.filter(Boolean).map(s => (
            <option key={s} value={s}>{s.replace('_', ' ')}</option>
          ))}
        </select>
      </div>

      <Table
        columns={columns}
        data={leads}
        loading={loading}
        error={error}
        onRetry={fetchLeads}
        emptyTitle="No leads found"
        emptyDescription="New enquiries from the website will appear here automatically."
        onRowClick={(row) => navigate(`/leads/${row.id}`)}
      />

      {/* Pagination */}
      {meta && meta.total > 20 && (
        <div className="flex items-center justify-between mt-4 text-sm text-slate-600">
          <span>Showing {leads.length} of {meta.total} leads</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
            >Previous</button>
            <span className="px-2 py-1">Page {page}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={leads.length < 20}
              className="rounded border border-slate-300 px-3 py-1 disabled:opacity-40 hover:bg-slate-50"
            >Next</button>
          </div>
        </div>
      )}

      {showNew && (
        <NewLeadModal
          onClose={() => setShowNew(false)}
          onCreated={(lead) => {
            setShowNew(false)
            toast('success', 'Lead created successfully')
            navigate(`/leads/${lead.id}`)
          }}
        />
      )}
    </div>
  )
}
