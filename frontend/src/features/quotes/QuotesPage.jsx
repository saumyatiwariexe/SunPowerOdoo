import React from 'react'
import { useNavigate } from 'react-router-dom'
import { api, formatPaise } from '../../app/api'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'
import { Collection, RecordDetail, recordLink, moneyLines } from '../../app/RecordPage'
export function QuotesPage() {
  const navigate = useNavigate()
  return (
    <Collection
      title="Quotes"
      path="/quotes"
      empty="No quotes yet. Create one after a site survey is approved."
      columns={[
        ['number', 'Quote', recordLink('/quotes', 'Quote')],
        ['customer_id', 'Customer ID'],
        ['valid_until', 'Valid until'],
        ['total_paise', 'Total'],
        ['status', 'Status'],
      ]}
      create={{
        label: 'Create quote',
        fields: [
          { name: 'lead_id', label: 'Approved lead ID', type: 'number', min: 1 },
          { name: 'package_id', label: 'Package ID', type: 'number', min: 1 },
          { name: 'valid_until', label: 'Valid until', type: 'date' },
          { name: 'subsidy_paise', label: 'Subsidy (₹)', type: 'money', value: 0 },
        ],
        action: (v) => api.post('/quotes', v),
        onDone: (r) => navigate('/quotes/' + r.id),
      }}
    />
  )
}
export function QuoteDetail() {
  const navigate = useNavigate()
  return (
    <RecordDetail title="Quotes" base="/quotes" singular="Quote" print>
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Customer ID', r.customer_id],
              ['Valid until', r.valid_until],
              ['Subtotal', formatPaise(r.subtotal_paise)],
              ['Subsidy', formatPaise(r.subsidy_paise)],
              ['Quote total', formatPaise(r.total_paise)],
            ]}
          />
          <h2>Bill of materials</h2>
          <DataTable rows={r.lines} columns={moneyLines} />
          {r.status === 'DRAFT' && (
            <>
              <details className="no-print">
                <summary>Edit line item</summary>
                <ActionForm
                  submit="Save line"
                  fields={[
                    {
                      name: 'line',
                      label: 'Item',
                      options: r.lines.map((l) => ({ value: l.id, label: l.description })),
                    },
                    { name: 'qty', label: 'Quantity', type: 'number', min: 1 },
                    { name: 'unit_price_paise', label: 'Unit price (₹)', type: 'money' },
                  ]}
                  action={({ line, ...v }) => api.patch(path, { lines: [{ id: Number(line), ...v }] })}
                  onDone={reload}
                />
              </details>
              <ActionForm
                primary
                submit="Mark quote as sent"
                action={() => api.post(path + '/send')}
                onDone={reload}
              />
            </>
          )}
          {['SENT', 'ACCEPTED'].includes(r.status) && (
            <ActionForm
              primary
              submit={r.status === 'SENT' ? 'Accept quote and open order' : 'Open order'}
              action={() => api.post(path + '/accept')}
              onDone={(order) => navigate('/orders/' + order.id)}
            />
          )}
        </>
      )}
    </RecordDetail>
  )
}
