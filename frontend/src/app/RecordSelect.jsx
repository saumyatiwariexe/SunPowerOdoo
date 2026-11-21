import React, { useEffect, useState } from 'react'
import { recordOptions } from './recordOptions'

export default function RecordSelect({ field, initial, busy, onAvailability, id, ...aria }) {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(!!field.lookup)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(() => field.multiple
    ? (initial || []).map(String) : String(initial ?? ''))
  useEffect(() => {
    if (!field.lookup) return
    let active = true
    setLoading(true)
    setError('')
    onAvailability(field.name, false)
    recordOptions(field.lookup).then((options) => {
      if (active) {
        setRows(options)
        setLoading(false)
        onAvailability(field.name, true)
      }
    }).catch((err) => {
      if (active) { setError(err.message); setLoading(false) }
    })
    return () => { active = false }
  }, [field.lookup, field.name, attempt, onAvailability])
  const options = field.lookup ? rows : field.options
  const chosen = (value) => field.multiple ? selected.includes(String(value)) : selected === String(value)
  const matches = options.filter((r) => `${r.label} ${r.detail || ''}`.toLowerCase().includes(query.toLowerCase()))
  const visible = options.filter((r) => matches.includes(r) || chosen(r.value))
  const missing = (field.multiple ? selected : [selected]).filter((value) => value && !options.some((r) => String(r.value) === value))
  return (
    <div className="record-picker">
      <input type="search" aria-label={'Search ' + field.label.toLowerCase()} placeholder="Search by name or reference…"
        value={query} onChange={(e) => setQuery(e.target.value)} disabled={busy || loading || !!error} />
      {loading && <small role="status">Loading choices…</small>}
      {error && <div role="alert" className="form-error">{error} <button type="button" className="text-link" onClick={() => setAttempt((v) => v + 1)}>Retry choices</button></div>}
      {field.multiple ? (
        <div id={id} role="group" aria-label={field.label} className="record-checks" {...aria}>
          {visible.map((row) => <label key={row.value} className="record-check">
            <input type="checkbox" name={field.name} value={row.value} checked={chosen(row.value)} disabled={busy || loading || !!error}
              onChange={(e) => setSelected((values) => e.target.checked ? [...values, String(row.value)] : values.filter((v) => v !== String(row.value)))} />
            <span>{row.label}<small>{row.detail}</small></span>
          </label>)}
          {missing.map((value) => <label key={value} className="record-check"><input type="checkbox" name={field.name} value={value} checked disabled={busy}
            onChange={() => setSelected((values) => values.filter((v) => v !== value))} /><span>Unavailable staff #{value} — remove to continue</span></label>)}
        </div>
      ) : (
        <select id={id} {...aria} name={field.name} value={selected} required={!field.optional} disabled={busy || loading || !!error}
          onChange={(e) => setSelected(e.target.value)}>
          <option value="" disabled={!field.optional}>{field.optional ? 'Unassigned' : 'Choose ' + field.label.toLowerCase()}</option>
          {missing.map((value) => <option key={value} value={value} disabled>Unavailable record #{value} — choose another</option>)}
          {visible.map((row) => <option key={row.value} value={row.value}>{row.label}{row.detail ? ' · ' + row.detail : ''}</option>)}
        </select>
      )}
      {!loading && !error && !matches.length && <small role="status">{options.length ? 'No matching results. Try another name or reference.' : field.empty || 'No eligible records available yet.'}</small>}
      {!field.multiple && options.filter((r) => chosen(r.value)).map((row) => <small key={row.value} className="record-selected">{row.label}<br />{row.detail}</small>)}
    </div>
  )
}
