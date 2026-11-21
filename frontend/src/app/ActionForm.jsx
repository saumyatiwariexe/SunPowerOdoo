import React, { useState } from 'react'
import { human } from './navigation'
import Field from './components/Field'

export function paise(text) {
  if (!/^\d+(\.\d{1,2})?$/.test(text))
    throw new Error('Enter a rupee amount with up to two decimal places.')
  const [whole, fraction = ''] = text.split('.')
  const amount = Number(whole + fraction.padEnd(2, '0'))
  if (!Number.isSafeInteger(amount)) throw new Error('Amount exceeds the supported range.')
  return amount
}
export default function ActionForm({
  fields = [],
  action,
  submit,
  onDone,
  initial = {},
  primary = false,
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [errors, setErrors] = useState({})
  async function save(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    setErrors({})
    const form = event.currentTarget
    try {
      const raw = new FormData(form)
      const values = {}
      for (const f of fields) {
        const text = raw.get(f.name)
        if (text == null || text === '' || (f.type === 'file' && !text.size)) continue
        if (f.type === 'money') values[f.name] = paise(text)
        else if (f.type === 'number') values[f.name] = Number(text)
        else if (f.type === 'datetime-local') values[f.name] = new Date(text).toISOString()
        else values[f.name] = typeof text === 'string' && f.type !== 'password' ? text.trim() : text
      }
      const response = await action(values)
      form.reset()
      onDone?.(response?.data)
    } catch (err) {
      setError(err.message || 'Could not save. Try again.')
      setErrors(
        Object.fromEntries(
          (err.details || []).map((d) => [d.field || d.loc?.at(-1), d.message || d.msg]),
        ),
      )
    } finally {
      setBusy(false)
    }
  }
  return (
    <form className="action-form no-print" onSubmit={save}>
      {fields.map((f) => {
        const props = {
          name: f.name,
          required: !f.optional,
          defaultValue: initial[f.name] ?? f.value ?? '',
          maxLength: f.maxLength,
          autoComplete: f.autoComplete,
          disabled: busy,
        }
        return (
          <Field key={f.name} label={f.label} error={errors[f.name]}>
            {f.options ? (
              <select {...props}>
                {f.placeholder && <option value="" disabled>{f.placeholder}</option>}
                {f.optional && <option value="">Unassigned</option>}
                {f.options.map((v) => (
                  <option key={v.value ?? v} value={v.value ?? v}>
                    {v.label ?? human(v)}
                  </option>
                ))}
              </select>
            ) : f.type === 'textarea' ? (
              <textarea {...props} rows="3" />
            ) : (
              <input
                {...props}
                type={f.type === 'money' ? 'number' : f.type || 'text'}
                step={f.step ?? (f.type === 'money' ? '0.01' : undefined)}
                min={f.min ?? (f.type === 'money' ? 0 : undefined)}
                max={f.max}
                accept={f.accept}
              />
            )}
          </Field>
        )
      })}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className={primary ? 'button primary' : 'button'} disabled={busy}>
        {busy ? 'Saving…' : submit}
      </button>
    </form>
  )
}
