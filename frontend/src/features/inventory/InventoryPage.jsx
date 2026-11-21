import React, { useState } from 'react'
import { api } from '../../app/api'
import { Collection } from '../../app/RecordPage'
export default function InventoryPage() {
  const [low, setLow] = useState(false)
  return (
    <Collection
      title="Stock"
      path={'/stock?low_stock=' + low}
      empty="No stock matches this view."
      tools={
        <div className="tools">
          <button className="filter" aria-pressed={low} onClick={() => setLow(!low)}>
            Low stock only
          </button>
        </div>
      }
      columns={[
        ['id', 'ID'],
        ['sku', 'SKU'],
        ['name', 'Product'],
        ['on_hand', 'On hand'],
        ['reorder_level', 'Reorder at'],
        ['low_stock', 'Stock level', (r) => (r.low_stock ? 'Low stock' : 'In stock')],
      ]}
      create={{
        label: 'Receive stock',
        fields: [
          { name: 'product_id', label: 'Product ID', type: 'number', min: 1 },
          { name: 'qty', label: 'Quantity', type: 'number', min: 1 },
          { name: 'purchase_cost_paise', label: 'Unit purchase cost (₹)', type: 'money' },
          { name: 'serials', label: 'Serial numbers (one per line)', type: 'textarea', optional: true },
        ],
        action: ({ serials, ...v }) =>
          api.post('/stock/receive', {
            ...v,
            serial_numbers: (serials || '')
              .split(/\r?\n/)
              .map((x) => x.trim())
              .filter(Boolean),
          }),
      }}
    />
  )
}
