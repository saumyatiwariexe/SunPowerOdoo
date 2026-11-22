import React from 'react'
import { Link } from 'react-router-dom'
import { api, formatPaise } from '../../app/api'
import ActionForm from '../../app/ActionForm'
import { Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink } from '../../app/RecordPage'
export function SubsidyPage() {
  return (
    <Collection
      title="Subsidy claims"
      path="/subsidy"
      empty="No subsidy claims recorded."
      columns={[
        ['id', 'Claim', recordLink('/subsidy', 'Claim')],
        ['scheme', 'Scheme'],
        ['customer_name', 'Customer'],
        ['order_number', 'Order', r => <Link className="text-link" to={`/orders/${r.order_id}`}>{r.order_number || r.order_id}</Link>],
        ['amount_paise', 'Amount'],
        ['reference_no', 'Reference'],
        ['status', 'Status'],
      ]}
    />
  )
}
export function SubsidyDetail() {
  return (
    <RecordDetail title="Subsidy claims" base="/subsidy" singular="Claim">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Scheme', r.scheme],
              ['Customer', r.customer_name],
              ['Order', <Link className="text-link" to={`/orders/${r.order_id}`}>{r.order_number || r.order_id}</Link>],
              ['Amount', formatPaise(r.amount_paise)],
              ['Reference', r.reference_no],
              ['Notes', r.notes],
            ]}
          />
          <ActionForm
            primary
            submit="Update claim"
            initial={{ ...r, amount_paise: (r.amount_paise / 100).toFixed(2) }}
            fields={[
              {
                name: 'status',
                label: 'Claim status',
                options: ['NOT_APPLIED', 'SUBMITTED', 'APPROVED', 'PAID', 'REJECTED'],
              },
              { name: 'scheme', label: 'Scheme' },
              { name: 'amount_paise', label: 'Claim amount (\u20b9)', type: 'money' },
              { name: 'reference_no', label: 'Reference number', optional: true },
              { name: 'notes', label: 'Notes', type: 'textarea', optional: true },
            ]}
            action={(v) =>
              api.patch(path, { ...v, reference_no: v.reference_no || null, notes: v.notes || null })
            }
            onDone={reload}
          />
        </>
      )}
    </RecordDetail>
  )
}
