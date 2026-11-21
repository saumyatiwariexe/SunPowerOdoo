import React, { useState } from 'react'
import { api } from '../../app/api.js'
import Modal from '../../app/components/Modal.jsx'
import Field, { textareaCls } from '../../app/components/Field.jsx'
import Spinner from '../../app/components/Spinner.jsx'

export default function MarkLostModal({ lead, onClose, onLost }) {
  const [reason,  setReason]  = useState('')
  const [error,   setError]   = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!reason.trim()) { setError('Please provide a reason for marking this lead as lost.'); return }
    setLoading(true)
    try {
      const { data } = await api.post(`/leads/${lead.id}/lost`, { lost_reason: reason.trim() })
      onLost(data)
    } catch (err) {
      setError(err.message || 'Failed to mark lead as lost')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="Mark Lead as Lost" onClose={onClose} size="sm">
      <div className="mb-4 rounded-lg bg-red-50 border border-red-100 px-3 py-2 text-sm text-red-700">
        ⚠️ This will mark the lead as <strong>LOST</strong>. It cannot be deleted but can be re-opened.
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Field label="Reason for loss" error={error} required>
          <textarea
            className={textareaCls}
            rows={3}
            value={reason}
            onChange={e => { setReason(e.target.value); setError('') }}
            placeholder="e.g. Customer chose a competitor, budget constraints…"
            disabled={loading}
            autoFocus
          />
        </Field>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-60"
          >
            {loading && <Spinner size="sm" />}
            {loading ? 'Marking…' : 'Mark as Lost'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
