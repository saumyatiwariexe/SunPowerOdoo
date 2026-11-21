import React from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, changedFields, formatPaise } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts, Heading, State } from '../../app/records'
import { Collection, RecordDetail } from '../../app/RecordPage'
import PackageEditor, { useProducts } from './PackageEditor'

const productFields = [
  { name: 'sku', label: 'SKU', maxLength: 64 },
  { name: 'name', label: 'Product name', maxLength: 120 },
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
  { name: 'unit', label: 'Unit', maxLength: 24 },
  { name: 'price_paise', label: 'Sale price (₹)', type: 'money' },
  { name: 'cost_paise', label: 'Cost (₹)', type: 'money' },
  { name: 'tracks_serial', label: 'Track serial numbers', options: ['No', 'Yes'] },
  { name: 'warranty_months', label: 'Warranty months', type: 'number', min: 1, optional: true },
  { name: 'reorder_level', label: 'Reorder level', type: 'number', min: 0, value: 0 },
]
const productPath = (id) => '/catalog/products/' + id
const productPayload = (v) => ({
  ...v,
  tracks_serial: v.tracks_serial === 'Yes',
  warranty_months: v.warranty_months ?? null,
})

export function CatalogPage() {
  const [params, setParams] = useSearchParams()
  const products = params.get('tab') === 'products'
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const director = currentUser.role === 'DIRECTOR'
  const path = products ? '/products' : '/packages'
  return (
    <Collection
      key={path}
      title="Catalog"
      path={path}
      tools={
        <div className="view-tabs">
          {['Packages', 'Products'].map((label) => (
            <button
              key={label}
              aria-pressed={products === (label === 'Products')}
              onClick={() => setParams(label === 'Products' ? { tab: 'products' } : {})}
            >
              {label}
            </button>
          ))}
        </div>
      }
      actions={
        !products &&
        director && (
          <Link className="button primary" to="/catalog/packages/new">
            Create package
          </Link>
        )
      }
      create={
        products &&
        director && {
          label: 'Add product',
          fields: productFields,
          action: (v) => api.post(path, productPayload(v)),
          onDone: (r) => navigate(productPath(r.id)),
        }
      }
      columns={[
        ['id', 'ID'],
        [
          'name',
          products ? 'Product' : 'Package',
          (r) => (
            <Link className="text-link" to={products ? productPath(r.id) : '/catalog/' + r.id}>
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
              ['active', 'Active'],
            ]),
        ['price_paise', 'Price'],
      ]}
    />
  )
}

export function ProductDetail() {
  const { currentUser } = useAuth()
  return (
    <RecordDetail title="Products" base="/products" backTo="/catalog?tab=products" singular="Product">
      {(r, path, reload) => (
        <>
          <h2>{r.name}</h2>
          <Facts
            items={[
              ['SKU', r.sku],
              ['Category', r.category],
              ['Unit', r.unit],
              ['On hand', r.on_hand],
              ['Sale price', formatPaise(r.price_paise)],
              ['Cost', formatPaise(r.cost_paise)],
              ['Serial tracking', r.tracks_serial ? 'Yes' : 'No'],
              ['Warranty (months)', r.warranty_months],
              ['Reorder level', r.reorder_level],
            ]}
          />
          {currentUser.role === 'DIRECTOR' && (
            <details>
              <summary>Edit product</summary>
              <ActionForm
                submit="Save product"
                primary
                fields={productFields}
                initial={{
                  ...r,
                  price_paise: (r.price_paise / 100).toFixed(2),
                  cost_paise: (r.cost_paise / 100).toFixed(2),
                  tracks_serial: r.tracks_serial ? 'Yes' : 'No',
                }}
                action={(v) => api.patch(path, changedFields(r, productPayload(v)))}
                onDone={reload}
              />
            </details>
          )}
        </>
      )}
    </RecordDetail>
  )
}

export function NewPackage() {
  const products = useProducts()
  const navigate = useNavigate()
  return (
    <>
      <Link className="back" to="/catalog">
        ← Catalog
      </Link>
      <Heading title="Create package" />
      <PackageEditor products={products} onDone={(r) => navigate('/catalog/' + r.id)} />
    </>
  )
}

export function PackageDetail() {
  const { currentUser } = useAuth()
  return (
    <RecordDetail title="Catalog" base="/packages" singular="Package" backTo="/catalog">
      {(r, path, reload) => (
        <PackageView key={r.id} row={r} reload={reload} director={currentUser.role === 'DIRECTOR'} />
      )}
    </RecordDetail>
  )
}

function PackageView({ row: r, director, reload }) {
  const [editing, setEditing] = React.useState(false)
  const products = useProducts()
  const names = new Map((products.data || []).map((product) => [product.id, product.name]))
  return (
    <>
      <h2>{r.name}</h2>
      <Facts
        items={[
          ['System type', r.system_type?.replace('_', '-') || 'Hardware only'],
          ['Capacity', r.capacity_kw ? r.capacity_kw + ' kW' : '—'],
          ['Price', formatPaise(r.price_paise)],
          ['Active', r.active ? 'Yes' : 'No'],
        ]}
      />
      {editing ? (
        <PackageEditor
          products={products}
          initial={r}
          onCancel={() => setEditing(false)}
          onDone={() => {
            setEditing(false)
            reload()
          }}
        />
      ) : (
        <>
          <h2>Bill of materials</h2>
          <State resource={products}>
            <DataTable
              rows={r.items}
              columns={[
                [
                  'product_id',
                  'Product',
                  (line) => (
                    <Link className="text-link" to={productPath(line.product_id)}>
                      {names.get(line.product_id) || 'Product #' + line.product_id}
                    </Link>
                  ),
                ],
                ['qty', 'Quantity'],
              ]}
            />
          </State>
          {director && (
            <div className="actions">
              <button className="button" onClick={() => setEditing(true)}>
                Edit package
              </button>
            </div>
          )}
        </>
      )}
    </>
  )
}
