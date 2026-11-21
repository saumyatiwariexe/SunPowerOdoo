import React, { useState } from 'react'
import { api } from '../../app/api.js'
import Modal from '../../app/components/Modal.jsx'
import Field, { inputCls, selectCls } from '../../app/components/Field.jsx'
import Spinner from '../../app/components/Spinner.jsx'

export default function NewLeadModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '', phone: '', source: 'WHATSAPP',
    requested_kw: '3', system_type: 'ON_GRID',
    subsidy_interest: false, notes: '',
  })
  const [errors,  setErrors]  = useState({})
  const [loading, setLoading] = useState(false)
  const [serverErr, setServerErr] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.name.trim())  e.name  = 'Customer name is required'
    if (!form.phone.trim()) e.phone = 'Phone number is required'
    else if (!/^[6-9]\d{9}$/.test(form.phone.trim())) e.phone = 'Enter a valid 10-digit number'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setServerErr('')
    try {
      const { data } = await api.post('/leads', {
        name:            form.name.trim(),
        phone:           form.phone.trim(),
        source:          form.source,
        requested_kw:    parseFloat(form.requested_kw),
        system_type:     form.system_type,
        subsidy_interest: form.subsidy_interest,
        notes:           form.notes.trim() || null,
      })
      onCreated(data)
    } catch (err) {
      if (err.details?.length) {
        const fe = {}
        err.details.forEach(d => { if (d.field) fe[d.field] = d.message })
        setErrors(fe)
      }
      setServerErr(err.message || 'Failed to create lead')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="New Lead" onClose={onClose}>
      {serverErr && (
        <div className="mb-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {serverErr}
        </div>
      )}
      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <Field label="Customer Name" error={errors.name} required>
          <input type="text" className={inputCls} value={form.name} onChange={e => set('name', e.target.value)} placeholder="Ramesh Sharma" disabled={loading} />
        </Field>
        <Field label="Phone" error={errors.phone} required>
          <input type="tel" className={inputCls} value={form.phone} onChange={e => set('phone', e.target.value)} placeholder="9876543210" maxLength={10} disabled={loading} />
        </Field>
        <Field label="Source" error={errors.source}>
          <select className={selectCls} value={form.source} onChange={e => set('source', e.target.value)} disabled={loading}>
            <option value="WHATSAPP">WhatsApp</option>
            <option value="CALL">Phone Call</option>
            <option value="WEB">Website</option>
          </select>
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Size (kW)">
            <select className={selectCls} value={form.requested_kw} onChange={e => set('requested_kw', e.target.value)} disabled={loading}>
              {['1','2','3','4','5'].map(k => <option key={k} value={k}>{k} kW</option>)}
            </select>
          </Field>
          <Field label="System Type">
            <select className={selectCls} value={form.system_type} onChange={e => set('system_type', e.target.value)} disabled={loading}>
              <option value="ON_GRID">On-Grid</option>
              <option value="OFF_GRID">Off-Grid</option>
            </select>
          </Field>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="rounded" checked={form.subsidy_interest} onChange={e => set('subsidy_interest', e.target.checked)} disabled={loading} />
          Interested in government subsidy
        </label>
        <Field label="Notes">
          <textarea className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-amber-500 focus:outline-none resize-none" rows={2} value={form.notes} onChange={e => set('notes', e.target.value)} placeholder="Any details from the conversation…" disabled={loading} />
        </Field>
        <div className="flex justify-end gap-3 pt-2">
          <button type="button" onClick={onClose} disabled={loading} className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50">
            Cancel
          </button>
          <button type="submit" disabled={loading} className="flex items-center gap-2 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 disabled:opacity-60">
            {loading && <Spinner size="sm" />}
            {loading ? 'Creating…' : 'Create Lead'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
