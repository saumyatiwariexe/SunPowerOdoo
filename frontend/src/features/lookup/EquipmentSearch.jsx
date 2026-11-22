import React, { useEffect, useState } from 'react'
import { api } from '../../app/api'
import { DataTable } from '../../app/records'

export default function EquipmentSearch({ onSelect, assignedOnly = false }) {
  const [query, setQuery] = useState('')
  const [rows, setRows] = useState([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let active = true
    setBusy(true)
    const timer = setTimeout(() => {
      api.get('/lookup/search', { q: query.trim(), assigned_only: assignedOnly }).then(r => {
        if (active) { setRows(r.data); setError('') }
      }).catch(e => { if (active) setError(e.message) }).finally(() => { if (active) setBusy(false) })
    }, 250)
    return () => { active = false; clearTimeout(timer) }
  }, [query, assignedOnly, revision])
  return <section className="stack">
    <label className="field">Find equipment by customer, phone or serial
      <input type="search" value={query} maxLength={100} onChange={e => setQuery(e.target.value)} placeholder="Type a name or part of the serial number" />
    </label>
    <p className="section-help">Showing up to 30 matches. Narrow your search to find a specific unit.</p>
    {busy ? <p role="status">Searching equipment...</p> : error ? <p role="alert">{error} <button className="button" onClick={() => setRevision(r => r + 1)}>Retry</button></p> : <DataTable rows={rows} columns={[
      ['serial_no', 'Serial'], ['product_name', 'Equipment'], ['customer_name', 'Customer'], ['customer_phone', 'Phone'], ['warranty_status', 'Warranty'],
      ['action', 'Action', row => <button type="button" className="button" onClick={() => onSelect(row)}>Select equipment</button>],
    ]} empty="No matching equipment. Try a customer name, phone or another serial." />}
  </section>
}
