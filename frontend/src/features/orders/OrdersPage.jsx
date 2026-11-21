import React from 'react'
import { api, formatPaise } from '../../app/api'
import { Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink } from '../../app/RecordPage'
import { PaymentForm } from '../invoices/InvoicesPage'
import ActionForm from '../../app/ActionForm'
export function OrdersPage() {
  return (
    <Collection
      title="Orders"
      path="/orders"
      empty="Accepted quotes appear here as draft orders."
      columns={[
        ['number', 'Order', recordLink('/orders', 'Order')],
        ['customer_id', 'Customer ID'],
        ['status', 'Status'],
        ['total_paise', 'Total'],
        ['advance_min_paise', 'Minimum advance'],
      ]}
    />
  )
}
export function OrderDetail() {
  return (
    <RecordDetail title="Orders" base="/orders" singular="Order">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Order ID', r.id],
              ['Quote ID', r.quote_id],
              ['Customer ID', r.customer_id],
              ['Total', formatPaise(r.total_paise)],
              ['Minimum advance', formatPaise(r.advance_min_paise)],
              ['Received', formatPaise(r.paid_paise)],
            ]}
          />
          <PaymentForm path={path} reload={reload} />
          {r.status === 'DRAFT' && r.paid_paise < r.advance_min_paise && (
            <p>Receive {formatPaise(r.advance_min_paise - r.paid_paise)} more to confirm this order.</p>
          )}
          {r.status === 'DRAFT' && r.paid_paise >= r.advance_min_paise && (
            <ActionForm
              primary
              submit="Confirm order"
              action={() => api.post(path + '/confirm')}
              onDone={reload}
            />
          )}
        </>
      )}
    </RecordDetail>
  )
}
