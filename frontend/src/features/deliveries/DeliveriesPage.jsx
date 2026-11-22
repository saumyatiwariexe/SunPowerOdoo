import React, { useState } from 'react'
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
              ['pick', 'Pick', ln => r.status === 'PENDING' && ln.tracks_serial && ln.scanned_serials.length < ln.qty_required && (hasRole(currentUser, 'WAREHOUSE') || hasRole(currentUser, 'DIRECTOR'))
                ? <AutoPickButton serial={ln.available_serials?.[0]} product={ln.product_name} path={path} reload={reload} /> : null],
            ]}
          />
          {r.status === 'PENDING' && (hasRole(currentUser, 'WAREHOUSE') || hasRole(currentUser, 'DIRECTOR')) && (
            <>
              <p className="section-help">Use “Pick next available” beside an item to assign its serial automatically. Scan a physical serial below when you need a specific unit.</p>
              <ActionForm
                submit="Scan serial"
                fields={[{ name: 'serial_no', label: 'Serial number' }]}
                action={(v) => api.post(path + '/scan', v)}
                onDone={reload}
              />
              {r.lines
                .flatMap((line) => line.scanned_serials)
                .map((s) => (
                  <ActionForm
                    key={s.serial_unit_id}
                    submit={'Remove ' + s.serial_no}
                    action={() => api.del(path + '/scan/' + s.serial_unit_id)}
                    onDone={reload}
                  />
                ))}
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

function AutoPickButton({ serial, product, path, reload }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function pick() {
    setBusy(true); setError('')
    try { await api.post(path + '/scan', { serial_no: serial }); reload() }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <span><button type="button" className="button" disabled={!serial || busy} onClick={pick}>{busy ? 'Picking…' : 'Pick next available'}</button>
    {!serial && <small role="status">No available {product} serials</small>}
    {error && <small role="alert" className="form-error">{error}</small>}
  </span>
}
