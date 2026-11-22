import React, { useEffect, useState } from 'react'
import { api } from '../../app/api'
import { DataTable } from '../../app/records'
import { Collection } from '../../app/RecordPage'
export default function InventoryPage() {
  const [low, setLow] = useState(false)
  const [search, setSearch] = useState('')
  const [searchDraft, setSearchDraft] = useState('')
  const [receipt, setReceipt] = useState(null)
  const [receivedProduct, setReceivedProduct] = useState(null)
  const [serialProduct, setSerialProduct] = useState(null)
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
        {receipt && <div role="status" className="stock-receipt">Received <strong>{receipt.added_qty}</strong> unit(s). New on-hand balance: <strong>{receipt.new_on_hand}</strong>.
          {!!receipt.serial_numbers?.length && <details><summary>View {receipt.serial_numbers.length} serial numbers</summary><ul>{receipt.serial_numbers.map(serial => <li key={serial}><code>{serial}</code></li>)}</ul></details>}
        </div>}
        {serialProduct && <SerialList product={serialProduct} onClose={() => setSerialProduct(null)} />}
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
        ['sku', 'SKU'],
        ['name', 'Product'],
        ['on_hand', 'On hand'],
        ['reorder_level', 'Reorder at'],
        ['low_stock', 'Stock level', (r) => (r.low_stock ? 'Low stock' : 'In stock')],
        ['tracks_serial', 'Serials', r => r.tracks_serial ? <button type="button" className="text-link" onClick={() => setSerialProduct(r)}>View serials</button> : 'Not tracked'],
      ]}
      create={{
        label: 'Receive stock',
        fields: [
          { name: 'product_id', label: 'Product', lookup: 'products' },
          { name: 'qty', label: 'Quantity', type: 'number', min: 1 },
          { name: 'purchase_cost_paise', label: 'Unit purchase cost (₹)', type: 'money' },
          { name: 'serials', label: 'Manufacturer serials (optional, one per line)', type: 'textarea', optional: true,
            hint: 'Leave blank to generate SunPower asset serials automatically. Enter printed serials when available for warranty lookup.' },
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

function SerialList({ product, onClose }) {
  const [rows, setRows] = useState(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    let active = true
    setRows(null); setError('')
    api.get('/stock/serials', { product_id: product.id, page, page_size: 20 })
      .then(result => { if (active) { setRows(result.data); setTotal(result.meta.total) } })
      .catch(err => { if (active) setError(err.message) })
    return () => { active = false }
  }, [product.id, page, attempt])
  return <section className="customer-payment-panel"><div className="section-line"><h3>{product.name} · serial units</h3><button type="button" className="button" onClick={onClose}>Close</button></div>
    {error ? <p role="alert" className="form-error">{error} <button type="button" onClick={() => setAttempt(n => n + 1)}>Retry</button></p>
      : rows === null ? <p role="status">Loading serials…</p> : <><DataTable rows={rows} columns={[["serial_no", "Serial number"], ["status", "Status"]]} empty="No serial units received yet." />
        <div className="tools"><button type="button" className="button" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>{page} of {Math.max(1, Math.ceil(total / 20))}</span><button type="button" className="button" disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>Next</button></div></>}
  </section>
}
