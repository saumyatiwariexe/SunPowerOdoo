import React, { useState } from 'react'
import { api } from '../../app/api.js'
import Field from '../../app/components/Field.jsx'
import { paise } from '../../app/ActionForm'

export default function CallChecklistForm({ lead, onCallLogged }) {
  const [form, setForm] = useState({
    shadow_free_area_sqm: '',
    monthly_bill_paise: '',
    grid_suitable: '',
    outcome: '',
    notes: '',
  })
  const [customOutcome, setCustomOutcome] = useState('')
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [serverErr, setServerErr] = useState('')

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.outcome || (form.outcome === 'Other' && !customOutcome.trim())) e.outcome = 'Choose an outcome or describe the call.'
    if (form.shadow_free_area_sqm && Number(form.shadow_free_area_sqm) <= 0) e.shadow_free_area_sqm = 'Enter a positive roof area.'
    if (form.monthly_bill_paise && !/^\d+(\.\d{1,2})?$/.test(form.monthly_bill_paise)) e.monthly_bill_paise = 'Enter an amount with up to two decimal places.'
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
        called_at: new Date().toISOString(),
        outcome: form.outcome === 'Other' ? customOutcome.trim() : form.outcome,
        notes: form.notes.trim() || null,
        shadow_free_area_sqm: form.shadow_free_area_sqm ? parseFloat(form.shadow_free_area_sqm) : null,
        monthly_bill_paise: form.monthly_bill_paise ? paise(form.monthly_bill_paise) : null,
        grid_suitable: form.grid_suitable !== '' ? form.grid_suitable === 'true' : null,
      }
      const { data } = await api.post(`/leads/${lead.id}/calls`, payload)
      onCallLogged(data)
      setCustomOutcome('')
      setForm({
        shadow_free_area_sqm: '',
        monthly_bill_paise: '',
        grid_suitable: '',
        outcome: '',
        notes: '',
      })
    } catch (err) {
      if (err.details?.length) {
        const fe = {}
        err.details.forEach((d) => {
          fe[d.field || d.loc?.at(-1)] = d.message || d.msg
        })
        setErrors(fe)
      }
      setServerErr(err.message || 'Failed to log call')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="call-checklist">
      <div>
        <h3>Quick call check-in</h3>
        <p>Tap the answers from your conversation. Add measurements only when known.</p>
      </div>
      {serverErr && <p role="alert" className="form-error">{serverErr}</p>}
      <QuickChoices label="How did the call go?" value={form.outcome} disabled={loading}
        onChange={(value) => { set('outcome', value); setErrors({}) }}
        choices={['Ready for a survey', 'Follow up later', 'No answer', 'Not interested', 'Other']} />
      {form.outcome === 'Other' && <Field label="Call outcome" required error={errors.outcome}>
        <input value={customOutcome} onChange={(e) => setCustomOutcome(e.target.value)} disabled={loading} placeholder="What did the customer say?" />
      </Field>}
      {errors.outcome && form.outcome !== 'Other' && <p role="alert" className="form-error">{errors.outcome}</p>}
      <QuickChoices label="Is the grid suitable?" value={form.grid_suitable} disabled={loading}
        onChange={(value) => set('grid_suitable', value)}
        choices={[{ value: 'true', label: 'Yes' }, { value: 'false', label: 'No' }, { value: '', label: 'Not assessed' }]} />
      <div className="call-measurements">
        <div>
          <QuickChoices label="Shadow-free roof area (m²)" value={form.shadow_free_area_sqm} disabled={loading}
            onChange={(value) => set('shadow_free_area_sqm', value)} choices={['20', '40', '60']} />
          <Field label="Exact roof area (optional)" error={errors.shadow_free_area_sqm}>
            <input type="number" min="0.1" step="any" value={form.shadow_free_area_sqm}
              onChange={(e) => set('shadow_free_area_sqm', e.target.value)} disabled={loading} placeholder="Not measured" />
          </Field>
        </div>
        <div>
          <QuickChoices label="Monthly electricity bill (₹)" value={form.monthly_bill_paise} disabled={loading}
            onChange={(value) => set('monthly_bill_paise', value)} choices={['1500', '3000', '5000']} />
          <Field label="Exact monthly bill (optional)" error={errors.monthly_bill_paise}>
            <input type="number" min="0" step="0.01" value={form.monthly_bill_paise}
              onChange={(e) => set('monthly_bill_paise', e.target.value)} disabled={loading} placeholder="Not known" />
          </Field>
        </div>
      </div>
      <details>
        <summary>Add a note (optional)</summary>
        <Field label="Call notes"><textarea value={form.notes} onChange={(e) => set('notes', e.target.value)} disabled={loading} rows={2} /></Field>
      </details>
      <div className="call-save">
        {lead.status === 'NEW' && <small>Saving this call marks the lead as contacted. You can then schedule a survey.</small>}
        <button type="submit" className="button primary" disabled={loading}>{loading ? 'Saving…' : 'Log Call'}</button>
      </div>
    </form>
  )
}

function QuickChoices({ label, choices, value, onChange, disabled }) {
  return <fieldset className="quick-question" disabled={disabled}>
    <legend>{label}</legend>
    <div className="quick-choices">
      {choices.map((choice) => {
        const item = typeof choice === 'string' ? { value: choice, label: choice } : choice
        return <button key={item.value} type="button" aria-pressed={value === item.value}
          onClick={() => onChange(item.value)}>{item.label}</button>
      })}
    </div>
  </fieldset>
}
