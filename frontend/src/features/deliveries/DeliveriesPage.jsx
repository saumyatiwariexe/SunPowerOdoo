import React from 'react'
import { api } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink } from '../../app/RecordPage'
export function DeliveriesPage() {
  return (
    <Collection
      title="Deliveries"
      path="/deliveries"
      empty="Confirmed orders appear here for picking."
      columns={[
        ['id', 'Delivery', recordLink('/deliveries', 'Delivery')],
        ['order_number', 'Order'],
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
              ['Order', r.order_number],
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
                    ? ln.scanned_serials.length + ' / ' + ln.qty_required
                    : 'Quantity only',
              ],
            ]}
          />
          {r.status === 'PENDING' && currentUser.role !== 'CREW' && (
            <>
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
