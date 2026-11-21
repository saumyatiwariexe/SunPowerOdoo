import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatPaise } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'
import { Collection, RecordDetail } from '../../app/RecordPage'

export function CatalogPage() {
  const [products, setProducts] = useState(false)
  const { currentUser } = useAuth()
  const canEdit = currentUser.role === 'DIRECTOR'
  const path = products ? '/products' : '/packages'
  const fields = [
    { name: 'sku', label: 'SKU' },
    { name: 'name', label: 'Product name' },
    {
      name: 'category',
      label: 'Category',
      options: [
        'PANEL',
        'INVERTER',
        'BATTERY',
        'CHARGE_CONTROLLER',
        'STAND',
        'WIRING',
        'SAFETY',
        'SERVICE',
      ],
    },
    { name: 'unit', label: 'Unit' },
    { name: 'price_paise', label: 'Sale price (₹)', type: 'money' },
    { name: 'cost_paise', label: 'Cost (₹)', type: 'money' },
    { name: 'tracks_serial', label: 'Track serial numbers', options: ['No', 'Yes'] },
    { name: 'warranty_months', label: 'Warranty months', type: 'number', min: 1, optional: true },
  ]
  const label = products ? 'Products' : 'Packages'
  return (
    <Collection
      key={path}
      title="Catalog"
      path={path}
      tools={
        <div className="view-tabs">
          {['Packages', 'Products'].map((x) => (
            <button key={x} aria-pressed={label === x} onClick={() => setProducts(x === 'Products')}>
              {x}
            </button>
          ))}
        </div>
      }
      create={
        products &&
        canEdit && {
          label: 'Add product',
          fields,
          action: (v) => api.post(path, { ...v, tracks_serial: v.tracks_serial === 'Yes' }),
        }
      }
      columns={[
        ['id', 'ID'],
        [
          'name',
          products ? 'Product' : 'Package',
          (r) =>
            products ? (
              r.name
            ) : (
              <Link className="text-link" to={'/catalog/' + r.id}>
                {r.name}
              </Link>
            ),
        ],
        ...(products
          ? [
              ['sku', 'SKU'],
              ['category', 'Category'],
              ['on_hand', 'On hand'],
            ]
          : [
              ['system_type', 'System'],
              ['capacity_kw', 'Capacity (kW)'],
            ]),
        ['price_paise', 'Price'],
      ]}
    />
  )
}
export function PackageDetail() {
  const { currentUser } = useAuth()
  return (
    <RecordDetail title="Catalog" base="/packages" singular="Package" backTo="/catalog">
      {(r, path, reload) => (
        <>
          <h2>{r.name}</h2>
          <Facts
            items={[
              ['Capacity', r.capacity_kw ? r.capacity_kw + ' kW' : 'Hardware only'],
              ['Price', formatPaise(r.price_paise)],
              ['Active', r.active ? 'Yes' : 'No'],
            ]}
          />
          <h2>Bill of materials</h2>
          <DataTable
            rows={r.items}
            columns={[
              ['product_id', 'Product ID'],
              ['qty', 'Quantity'],
            ]}
          />
          {currentUser.role === 'DIRECTOR' && (
            <details>
              <summary>Edit bill of materials</summary>
              <ActionForm
                submit="Save bill of materials"
                fields={[
                  {
                    name: 'items',
                    label: 'Product ID and quantity, one pair per line (e.g. 12, 2)',
                    type: 'textarea',
                    value: r.items.map((i) => i.product_id + ', ' + i.qty).join('\n'),
                  },
                ]}
                action={(v) => {
                  const items = v.items.split(/\r?\n/).map((line) => {
                    const match = /^\s*(\d+)\s*,\s*(\d+)\s*$/.exec(line)
                    if (!match) throw new Error('Enter a product ID and quantity on each line.')
                    return { product_id: Number(match[1]), qty: Number(match[2]) }
                  })
                  return api.patch(path, { items })
                }}
                onDone={reload}
              />
            </details>
          )}
        </>
      )}
    </RecordDetail>
  )
}
