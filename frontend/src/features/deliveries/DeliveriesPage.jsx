import React, { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import { hasRole } from '../../app/navigation'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink } from '../../app/RecordPage'
export function DeliveriesPage() {
  const [status, setStatus] = useState('PENDING')
  return (
    <Collection
      title="Deliveries"
      key={status}
      path={'/deliveries' + (status ? '?status=' + status : '')}
      tools={<label className="field">Delivery status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">All deliveries</option>{['PENDING', 'DISPATCHED', 'DELIVERED'].map(s => <option key={s} value={s}>{s}</option>)}</select></label>}
      empty="Confirmed orders appear here for picking."
      columns={[
        ['id', 'Delivery', recordLink('/deliveries', 'Delivery')],
        ['customer_name', 'Customer'],
        ['order_number', 'Order', r => <Link className="text-link" to={`/orders/${r.order_id}`}>{r.order_number}</Link>],
        ['status', 'Status'],
        ['vehicle', 'Vehicle'],
        ['delivered_at', 'Delivered'],
      ]}
    />
  )
}
export function DeliveryDetail() {
  const { currentUser } = useAuth()
  return (
    <RecordDetail title="Deliveries" base="/deliveries" singular="Delivery">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Customer', r.customer?.name],
              ['Phone', r.customer?.phone],
              ['Site', [r.customer?.address, r.customer?.city, r.customer?.pincode].filter(Boolean).join(', ')],
              ['Order', <Link className="text-link" to={`/orders/${r.order_id}`}>{r.order_number}</Link>],
              ['Vehicle', r.vehicle],
            ]}
          />
          <h2>Pick list</h2>
          <DataTable
            rows={r.lines}
            columns={[
              ['product_name', 'Product'],
              ['sku', 'SKU'],
              ['qty_required', 'Required'],
              [
                'scans',
                'Serials scanned',
                (ln) =>
                  ln.tracks_serial
                    ? <span>{ln.scanned_serials.length} / {ln.qty_required}{ln.scanned_serials.length > 0 && <small className="record-selected">{ln.scanned_serials.map(scan => scan.serial_no).join(', ')}</small>}</span>
                    : 'Quantity only',
              ],
            ]}
          />
          {r.status === 'PENDING' && (hasRole(currentUser, 'WAREHOUSE') || hasRole(currentUser, 'DIRECTOR')) && (
            <>
              <AutoFillOnOpen key={path} path={path} reload={reload} />
              {r.lines.some(line => line.tracks_serial && line.scanned_serials.length < line.qty_required) &&
                <p className="section-help">Any remaining serials will be assigned automatically when matching stock is received and this delivery is reopened.</p>}
              {r.lines.every((l) => !l.tracks_serial || l.scanned_serials.length === l.qty_required) && (
                <ActionForm
                  primary
                  submit="Dispatch delivery"
                  fields={[{ name: 'vehicle', label: 'Vehicle', optional: true }]}
                  action={(v) => api.post(path + '/dispatch', v)}
                  onDone={reload}
                />
              )}
            </>
          )}
          {r.status === 'DISPATCHED' && (
            <ActionForm
              primary
              submit="Mark delivered"
              action={() => api.post(path + '/deliver')}
              onDone={reload}
            />
          )}
        </>
      )}
    </RecordDetail>
  )
}

function AutoFillOnOpen({ path, reload }) {
  const started = useRef(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function fill() {
    setBusy(true); setError('')
    try { await api.post(path + '/auto-fill', {}); reload() }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  useEffect(() => { if (!started.current) { started.current = true; fill() } }, [path])
  return <p role={error ? 'alert' : 'status'} className={error ? 'form-error' : 'section-help'}>
    {error ? <>Automatic assignment failed: {error} <button type="button" className="text-link" onClick={fill}>Retry</button></>
      : busy ? 'Assigning available serials…' : 'Available serials have been assigned.'}
  </p>
}
