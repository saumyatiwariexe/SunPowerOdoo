import React from 'react'
import { useNavigate } from 'react-router-dom'
import { api, formatPaise } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink, moneyLines } from '../../app/RecordPage'
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
        currentUser.role !== 'SUPPORT' && {
          label: 'Create invoice',
          fields: [{ name: 'order_id', label: 'Order ID', type: 'number', min: 1 }],
          action: (v) => api.post('/invoices', v),
          onDone: (r) => navigate('/invoices/' + r.id),
        }
      }
      columns={[
        ['number', 'Invoice', recordLink('/invoices', 'Invoice')],
        ['customer_name', 'Customer'],
        ['total_paise', 'Total'],
        ['balance_paise', 'Balance'],
        ['status', 'Status'],
      ]}
    />
  )
}
export function InvoiceDetail() {
  return (
    <RecordDetail title="Invoices" base="/invoices" singular="Invoice" print>
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Billed to', r.customer?.name],
              ['Address', r.customer?.address],
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
          {r.balance_paise > 0 && <PaymentForm path={path} reload={reload} />}
        </>
      )}
    </RecordDetail>
  )
}
