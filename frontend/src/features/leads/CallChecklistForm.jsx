import React, { useState } from 'react'
import { api } from '../../app/api.js'
import Field, { inputCls, selectCls, textareaCls } from '../../app/components/Field.jsx'
import Spinner from '../../app/components/Spinner.jsx'

export default function CallChecklistForm({ lead, onCallLogged }) {
  const [form, setForm] = useState({
    shadow_free_area_sqm:  '',
    monthly_bill_paise:    '',
    grid_suitable:         '',
    outcome:               '',
    notes:                 '',
  })
  const [errors,  setErrors]  = useState({})
  const [loading, setLoading] = useState(false)
  const [serverErr, setServerErr] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.outcome.trim()) e.outcome = 'Outcome is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setServerErr('')
    try {
      const payload = {
        outcome: form.outcome.trim(),
        notes:   form.notes.trim() || null,
        shadow_free_area_sqm: form.shadow_free_area_sqm ? parseFloat(form.shadow_free_area_sqm) : null,
        monthly_bill_paise:   form.monthly_bill_paise   ? Math.round(parseFloat(form.monthly_bill_paise) * 100) : null,
        grid_suitable:        form.grid_suitable !== '' ? form.grid_suitable === 'true' : null,
      }
      const { data } = await api.post(`/leads/${lead.id}/calls`, payload)
      onCallLogged(data)
      setForm({ shadow_free_area_sqm: '', monthly_bill_paise: '', grid_suitable: '', outcome: '', notes: '' })
    } catch (err) {
      if (err.details?.length) {
        const fe = {}
        err.details.forEach(d => { if (d.field) fe[d.field] = d.message })
        setErrors(fe)
      }
      setServerErr(err.message || 'Failed to log call')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-5">
      <h3 className="text-sm font-semibold text-slate-800 mb-4">Log Call / Site Assessment</h3>

      {serverErr && (
        <div className="mb-3 rounded-lg bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {serverErr}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Shadow-free Area (m²)" error={errors.shadow_free_area_sqm}>
            <input
              type="number"
              className={inputCls}
              value={form.shadow_free_area_sqm}
              onChange={e => set('shadow_free_area_sqm', e.target.value)}
              placeholder="e.g. 25"
              min="0"
              step="0.5"
              disabled={loading}
            />
          </Field>

          <Field label="Monthly Bill (₹)" error={errors.monthly_bill_paise}>
            <input
              type="number"
              className={inputCls}
              value={form.monthly_bill_paise}
              onChange={e => set('monthly_bill_paise', e.target.value)}
              placeholder="e.g. 3500"
              min="0"
              disabled={loading}
            />
          </Field>
        </div>

        <Field label="Grid Suitable?" error={errors.grid_suitable}>
          <select className={selectCls} value={form.grid_suitable} onChange={e => set('grid_suitable', e.target.value)} disabled={loading}>
            <option value="">— not assessed —</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </Field>

        <Field label="Call Outcome" error={errors.outcome} required>
          <input
            type="text"
            className={inputCls}
            value={form.outcome}
            onChange={e => set('outcome', e.target.value)}
            placeholder="e.g. Interested, will confirm in 2 days"
            disabled={loading}
          />
        </Field>

        <Field label="Notes" error={errors.notes}>
          <textarea
            className={textareaCls}
            rows={2}
            value={form.notes}
            onChange={e => set('notes', e.target.value)}
            placeholder="Additional notes from the call…"
            disabled={loading}
          />
        </Field>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-amber-500 px-5 py-2 text-sm font-semibold text-white hover:bg-amber-600 disabled:opacity-60 transition-colors"
          >
            {loading && <Spinner size="sm" />}
            {loading ? 'Saving…' : 'Log Call'}
          </button>
        </div>
      </form>
    </div>
  )
}
