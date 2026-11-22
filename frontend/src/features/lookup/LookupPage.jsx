import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../../app/AuthContext'
import { hasRole } from '../../app/navigation'
import EquipmentSearch from './EquipmentSearch'
import { DataTable, Heading, State, useRecord } from '../../app/records'
export default function LookupPage() {
  const [searchParams] = useSearchParams()
  const { currentUser } = useAuth()
  const [query, setQuery] = useState('')
  const result = useRecord(query && '/lookup?' + query)
  const rows = Array.isArray(result.data) ? result.data : result.data ? [result.data] : []
  function find(event) {
    event.preventDefault()
    const f = new FormData(event.currentTarget)
    const next = new URLSearchParams({ [f.get('by')]: f.get('term').trim() }).toString()
    if (next === query) result.reload(); else setQuery(next)
  }
  return (
    <>
      <Heading title="Serial lookup" />
      <form className="tools" onSubmit={find}>
        <select name="by" aria-label="Look up by">
          <option value="serial">Serial number</option>
          <option value="phone">Customer phone</option>
        </select>
        <input
          name="term"
          required
          maxLength="100"
          aria-label="Search value"
          placeholder="Enter serial or phone"
        />
        <button className="button primary">Look up</button>
      </form>
      <EquipmentSearch initialQuery={searchParams.get('q') || ''} onSelect={row => setQuery(new URLSearchParams({ serial: row.serial_no }).toString())} />
      {query && (
        <State resource={result}>
          <DataTable
            rows={rows}
            empty="No equipment matches this search."
            columns={[
              ['serial_no', 'Serial number'],
              ['product_name', 'Product'],
              ['customer_name', 'Customer'],
              ['warranty_status', 'Warranty'],
              ['end_date', 'Coverage ends'],
              [
                'action',
                '',
                (r) =>
                  r.customer_id &&
                  (hasRole(currentUser, 'SUPPORT') || hasRole(currentUser, 'DIRECTOR')) && (
                    <Link
                      className="text-link"
                      to={'/tickets?new=1&serial=' + encodeURIComponent(r.serial_no)}
                    >
                      Create ticket
                    </Link>
                  ),
              ],
            ]}
          />
        </State>
      )}
    </>
  )
}
