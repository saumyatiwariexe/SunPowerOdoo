import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api, formatPaise } from '../../app/api.js'
import PageHeader from '../../app/components/PageHeader.jsx'
import Badge from '../../app/components/Badge.jsx'
import Spinner from '../../app/components/Spinner.jsx'
import MarkLostModal from './MarkLostModal.jsx'
import CallChecklistForm from './CallChecklistForm.jsx'
import { toast } from '../../app/components/Toast.jsx'

const SOURCE_BADGE = { WEB: 'info', WHATSAPP: 'success', CALL: 'warning' }
const STATUS_BADGE = {
  NEW: 'neutral', CONTACTED: 'info', SURVEY_PENDING: 'warning',
  SURVEY_DONE: 'info', QUOTED: 'info', WON: 'success', LOST: 'danger',
}

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [lead,    setLead]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [showLost, setShowLost] = useState(false)
  const [requesting, setRequesting] = useState(false)

  const fetchLead = async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get(`/leads/${id}`)
      setLead(data)
    } catch (err) {
      setError(err.message || 'Failed to load lead')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLead() }, [id]) // eslint-disable-line

  const handleRequestSurvey = async () => {
    setRequesting(true)
    try {
      const { data } = await api.patch(`/leads/${id}`, { status: 'SURVEY_PENDING' })
      setLead(data)
      toast('success', 'Survey requested successfully')
    } catch (err) {
      toast('error', err.message || 'Failed to request survey')
    } finally {
      setRequesting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    )
  }

  if (error || !lead) {
    return (
      <div className="flex flex-col h-64 items-center justify-center gap-3">
        <span className="text-4xl">⚠️</span>
        <p className="text-sm text-slate-600">{error || 'Lead not found'}</p>
        <button onClick={fetchLead} className="rounded-lg bg-amber-500 px-4 py-2 text-sm text-white hover:bg-amber-600">Retry</button>
      </div>
    )
  }

  const isTerminal = ['WON', 'LOST'].includes(lead.status)
  const canSurvey  = ['CONTACTED', 'NEW'].includes(lead.status)
  const canLost    = !['LOST', 'WON'].includes(lead.status)

  return (
    <div>
      <PageHeader
        title={lead.customer?.name || `Lead #${lead.id}`}
        subtitle={`Lead #${lead.id} · ${new Date(lead.created_at).toLocaleDateString('en-IN')}`}
        action={
          <button onClick={() => navigate(-1)} className="text-sm text-slate-500 hover:text-slate-800">← Back to Leads</button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Customer Info + Status */}
        <div className="lg:col-span-1 flex flex-col gap-4">
          {/* Status card */}
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <div className="flex items-center justify-between mb-4">
              <Badge variant={STATUS_BADGE[lead.status]} label={lead.status?.replace('_', ' ')} />
              <Badge variant={SOURCE_BADGE[lead.source]} label={lead.source} />
            </div>

            <div className="space-y-2 text-sm">
              <InfoRow label="Requested"   value={lead.requested_kw ? `${lead.requested_kw} kW` : '—'} />
              <InfoRow label="System Type" value={lead.system_type?.replace('_', '-') || '—'} />
              <InfoRow label="Subsidy"     value={lead.subsidy_interest ? '✅ Interested' : '❌ Not interested'} />
              {lead.lost_reason && (
                <div className="mt-3 rounded-lg bg-red-50 border border-red-100 p-3">
                  <p className="text-xs font-medium text-red-700">Lost reason:</p>
                  <p className="text-xs text-red-600 mt-0.5">{lead.lost_reason}</p>
                </div>
              )}
            </div>

            {/* Action buttons */}
            {!isTerminal && (
              <div className="mt-5 flex flex-col gap-2">
                {canSurvey && (
                  <button
                    onClick={handleRequestSurvey}
                    disabled={requesting}
                    className="flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 disabled:opacity-60 transition-colors"
                  >
                    {requesting && <Spinner size="sm" />}
                    Request Survey
                  </button>
                )}
                {canLost && (
                  <button
                    onClick={() => setShowLost(true)}
                    className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                  >
                    Mark as Lost
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Customer card */}
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">Customer Info</h3>
            <div className="space-y-2 text-sm">
              <InfoRow label="Name"    value={lead.customer?.name || '—'} />
              <InfoRow label="Phone"   value={lead.customer?.phone || '—'} />
              <InfoRow label="Address" value={lead.customer?.address || '—'} />
              <InfoRow label="Pincode" value={lead.customer?.pincode || '—'} />
            </div>
          </div>
        </div>

        {/* Right: Timeline + Call Checklist */}
        <div className="lg:col-span-2 flex flex-col gap-4">
          {/* Call checklist form */}
          {!isTerminal && (
            <CallChecklistForm
              lead={lead}
              onCallLogged={(call) => {
                setLead(prev => ({
                  ...prev,
                  calls: [call, ...(prev.calls || [])],
                  status: prev.status === 'NEW' ? 'CONTACTED' : prev.status,
                }))
                toast('success', 'Call logged successfully')
              }}
            />
          )}

          {/* Call history timeline */}
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <h3 className="text-sm font-semibold text-slate-700 mb-4">Call History</h3>
            {(!lead.calls || lead.calls.length === 0) ? (
              <p className="text-sm text-slate-400 text-center py-6">No calls logged yet</p>
            ) : (
              <div className="space-y-4">
                {lead.calls.map((call, i) => (
                  <div key={call.id ?? i} className="relative pl-5 border-l-2 border-amber-200">
                    <div className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-amber-400" />
                    <div className="text-xs text-slate-400 mb-1">
                      {new Date(call.called_at || call.created_at).toLocaleString('en-IN')}
                      {call.called_by && ` · ${call.called_by.name}`}
                    </div>
                    <p className="text-sm font-medium text-slate-800">{call.outcome}</p>
                    {call.notes && <p className="text-xs text-slate-500 mt-0.5">{call.notes}</p>}
                    <div className="flex flex-wrap gap-3 mt-2">
                      {call.shadow_free_area_sqm != null && (
                        <span className="text-xs text-slate-500">📐 {call.shadow_free_area_sqm} m²</span>
                      )}
                      {call.monthly_bill_paise != null && (
                        <span className="text-xs text-slate-500">💡 {formatPaise(call.monthly_bill_paise)}/mo</span>
                      )}
                      {call.grid_suitable != null && (
                        <span className="text-xs text-slate-500">
                          {call.grid_suitable ? '✅ Grid suitable' : '❌ Grid not suitable'}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {showLost && (
        <MarkLostModal
          lead={lead}
          onClose={() => setShowLost(false)}
          onLost={(updated) => {
            setLead(updated)
            setShowLost(false)
            toast('info', 'Lead marked as lost')
          }}
        />
      )}
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-slate-500 shrink-0">{label}</span>
      <span className="text-slate-800 text-right">{value}</span>
    </div>
  )
}
