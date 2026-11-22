import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, formatPaise } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import { hasRole } from '../../app/navigation'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink, moneyLines } from '../../app/RecordPage'
import CustomerPayments from '../public/CustomerPayments'
export function PaymentForm({ path, reload }) {
  return (
    <details className="no-print">
      <summary>Record payment</summary>
      <ActionForm
        primary
        submit="Record payment"
        fields={[
          { name: 'amount_paise', label: 'Amount (₹)', type: 'money', min: 0.01 },
          { name: 'method', label: 'Payment method', options: ['UPI', 'CASH', 'CARD', 'BANK'] },
          { name: 'reference', label: 'Payment reference', optional: true },
        ]}
        action={(v) => api.post(path + '/payments', v)}
        onDone={reload}
      />
    </details>
  )
}
export function InvoicesPage() {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  return (
    <Collection
      title="Invoices"
      path="/invoices"
      empty="No invoices issued."
      create={
        (hasRole(currentUser, 'SALES') || hasRole(currentUser, 'DIRECTOR')) && {
          label: 'Create invoice',
          fields: [{ name: 'order_id', label: 'Customer order', lookup: 'orders' }],
          action: (v) => api.post('/invoices', v),
          onDone: (r) => navigate('/invoices/' + r.id),
        }
      }
      columns={[
        ['number', 'Invoice', recordLink('/invoices', 'Invoice')],
        ['customer_name', 'Customer'],
        ['order_id', 'Order', r => r.order_id ? <Link className="text-link" to={`/orders/${r.order_id}`}>View order</Link> : 'Service ticket'],
        ['total_paise', 'Total'],
        ['balance_paise', 'Balance'],
        ['status', 'Status'],
      ]}
    />
  )
}
export function InvoiceDetail() {
  const { currentUser } = useAuth()
  return (
    <RecordDetail title="Invoices" base="/invoices" singular="Invoice" print>
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Billed to', r.customer?.name],
              ['Phone', r.customer?.phone],
              ['Address', r.customer?.address],
              ['Order', r.order_id ? <Link className="text-link" to={`/orders/${r.order_id}`}>View order</Link> : 'Service ticket'],
              ['Issued', new Date(r.issued_at).toLocaleDateString('en-IN')],
              ['Invoice total', formatPaise(r.total_paise)],
              ['Paid', formatPaise(r.paid_paise)],
              ['Balance due', formatPaise(r.balance_paise)],
            ]}
          />
          <h2>Invoice items</h2>
          <DataTable rows={r.lines} columns={moneyLines} />
          <h2>Payments</h2>
          <DataTable
            rows={r.payments}
            columns={[
              ['method', 'Method'],
              ['amount_paise', 'Amount'],
              ['reference', 'Reference'],
            ]}
            empty="No payments recorded."
          />
            {(hasRole(currentUser, 'SALES') || hasRole(currentUser, 'DIRECTOR')) && <CustomerPayments kind="invoices" id={r.id} staff onChange={reload} />}
            {r.balance_paise > 0 && <PaymentForm path={path} reload={reload} />}
        </>
      )}
    </RecordDetail>
  )
}
