import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatPaise } from '../../app/api'
import { Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink } from '../../app/RecordPage'
import { PaymentForm } from '../invoices/InvoicesPage'
import ActionForm from '../../app/ActionForm'
import CustomerPayments from '../public/CustomerPayments'
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
          <OrderConnections orderId={r.id} status={r.status} />
          <CustomerPayments kind="orders" id={r.id} staff onChange={reload} />
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

function OrderConnections({ orderId, status }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api.get(`/orders/${orderId}/connections`).then(r => setData(r.data)).catch(() => setData(null)) }, [orderId, status])
  if (!data) return null
  return <section><p>Customer: <strong>{data.customer_name}</strong></p><div className="tools">
    {data.delivery_id && <Link className="button" to={`/deliveries/${data.delivery_id}`}>View delivery</Link>}
    {data.invoice_id && <Link className="button" to={`/invoices/${data.invoice_id}`}>View invoice</Link>}
    {!data.invoice_id && status !== 'DRAFT' && <button className="button" disabled={busy} onClick={async () => {
      setBusy(true); setError('')
      try { const result = await api.post('/invoices', { order_id: orderId }); setData(d => ({ ...d, invoice_id: result.data.id })) }
      catch (e) { setError(e.message) } finally { setBusy(false) }
    }}>{busy ? 'Creating invoice…' : 'Create invoice for this order'}</button>}
    {data.subsidy_claim_id && <Link className="button" to={`/subsidy/${data.subsidy_claim_id}`}>View subsidy claim</Link>}
  </div>{error && <p role="alert" className="form-error">{error}</p>}</section>
}
