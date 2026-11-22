import React, { useState } from 'react'
import { api } from '../../app/api'
import { Collection } from '../../app/RecordPage'
export default function InventoryPage() {
  const [low, setLow] = useState(false)
  const [search, setSearch] = useState('')
  const [searchDraft, setSearchDraft] = useState('')
  const [receipt, setReceipt] = useState(null)
  const [receivedProduct, setReceivedProduct] = useState(null)
  const params = new URLSearchParams({ low_stock: low })
  if (search.trim()) params.set('q', search.trim())
  if (receivedProduct) params.set('product_id', receivedProduct)
  return (
    <Collection
      key={params.toString()}
      title="Stock"
      path={'/stock?' + params}
      empty="No stock matches this view."
      tools={
        <>
        {receipt && <p role="status" className="stock-receipt">Received <strong>{receipt.added_qty}</strong> unit(s) for product #{receipt.product_id}. New on-hand balance: <strong>{receipt.new_on_hand}</strong>.</p>}
        <div className="tools">
          <form className="search-box" role="search" onSubmit={e => { e.preventDefault(); setSearch(searchDraft); setReceivedProduct(null) }}>
            <input type="search" aria-label="Search stock by name or SKU" placeholder="Search product name or SKU" value={searchDraft} onChange={e => setSearchDraft(e.target.value)} />
            <button type="submit">Search</button>
          </form>
          <button className="filter" aria-pressed={low} onClick={() => { setLow(!low); setReceivedProduct(null) }}>
            Low stock only
          </button>
          {receivedProduct && <button className="button" onClick={() => setReceivedProduct(null)}>Show all stock</button>}
        </div>
        </>
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
          { name: 'product_id', label: 'Product', lookup: 'products' },
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
        onDone: result => {
          setReceipt(result)
          setSearch('')
          setSearchDraft('')
          setLow(false)
          setReceivedProduct(result.product_id)
        },
      }}
    />
  )
}
