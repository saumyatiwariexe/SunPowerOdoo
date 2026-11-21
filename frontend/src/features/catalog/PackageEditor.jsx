import React, { useState } from 'react'
import { api, changedFields } from '../../app/api'
import { paise } from '../../app/ActionForm'
import Field from '../../app/components/Field'
import { State, useRecord } from '../../app/records'

async function allProducts(path) {
  const rows = []
  let page = 1
  for (;;) {
    const { data, meta } = await api.get(path, { page, page_size: 100 })
    rows.push(...data)
    if (!data.length || rows.length >= meta.total) return { data: rows }
    page += 1
  }
}

export function useProducts() {
  return useRecord('/products', allProducts)
}

export default function PackageEditor({ initial, onDone, onCancel, products }) {
  const [type, setType] = useState(initial?.system_type || '')
  const [lines, setLines] = useState(
    initial?.items.map((i) => ({ product_id: String(i.product_id), qty: i.qty })) || [
      { product_id: '', qty: 1 },
    ],
  )
  const [error, setError] = useState('')
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const catalog = products.data || []
  const install = catalog.find((p) => p.sku === 'INSTALLATION')
  const requiredId = type && install ? String(install.id) : null

  function changeType(next) {
    setType(next)
    if (next && install && !lines.some((line) => line.product_id === String(install.id))) {
      setLines([...lines, { product_id: String(install.id), qty: 1 }])
    }
  }
  function editLine(index, key, value) {
    setLines(lines.map((line, i) => (i === index ? { ...line, [key]: value } : line)))
  }
  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setError('')
    setErrors({})
    setBusy(true)
    const form = new FormData(event.currentTarget)
    try {
      const payload = {
        name: form.get('name').trim(),
        price_paise: paise(form.get('price')),
        system_type: type || null,
        capacity_kw: type ? Number(form.get('capacity')) : null,
        active: form.get('active') === 'on',
        items: lines.map((line) => ({ product_id: Number(line.product_id), qty: Number(line.qty) })),
      }
      let response
      if (initial) {
        const changes = changedFields(initial, payload)
        const quantities = new Map(initial.items.map((item) => [item.product_id, item.qty]))
        if (
          quantities.size === payload.items.length &&
          payload.items.every((item) => quantities.get(item.product_id) === item.qty)
        ) {
          delete changes.items
        }
        response = await api.patch('/packages/' + initial.id, changes)
      } else {
        response = await api.post('/packages', payload)
      }
      onDone(response.data)
    } catch (err) {
      setError(err.message || 'Could not save the package.')
      setErrors(Object.fromEntries((err.details || []).map((d) => [d.loc?.[1] || d.field, d.message])))
    } finally {
      setBusy(false)
    }
  }
  return (
    <State resource={products}>
      {catalog.length ? (
        <form className="action-form" onSubmit={submit}>
          <Field label="Package name" error={errors.name}>
            <input name="name" required maxLength={120} defaultValue={initial?.name} />
          </Field>
          <Field label="Package price (₹)" error={errors.price_paise}>
            <input
              type="number"
              name="price"
              min="0"
              step="0.01"
              required
              defaultValue={initial ? (initial.price_paise / 100).toFixed(2) : ''}
            />
          </Field>
          <Field label="System type">
            <select value={type} onChange={(e) => changeType(e.target.value)}>
              <option value="">Hardware only</option>
              <option value="ON_GRID">On-grid</option>
              <option value="OFF_GRID">Off-grid</option>
            </select>
          </Field>
          {type && (
            <Field label="Capacity (kW)" error={errors.capacity_kw}>
              <input
                type="number"
                name="capacity"
                min="1"
                max="5"
                required
                defaultValue={initial?.capacity_kw || 1}
              />
            </Field>
          )}
          <label>
            <input type="checkbox" name="active" defaultChecked={initial?.active ?? true} /> Active
            package
          </label>
          <fieldset className="stack">
            <legend>Bill of materials</legend>
            {lines.map((line, i) => (
              <div className="bom-line" key={i}>
                <Field label={'Product ' + (i + 1)}>
                  <select
                    value={line.product_id}
                    required
                    disabled={line.product_id === requiredId}
                    onChange={(e) => editLine(i, 'product_id', e.target.value)}
                  >
                    <option value="">Choose product</option>
                    {catalog.map((p) => (
                      <option
                        key={p.id}
                        value={p.id}
                        disabled={lines.some((other, j) => j !== i && other.product_id === String(p.id))}
                      >
                        {p.name} · {p.sku}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label={'Quantity ' + (i + 1)}>
                  <input
                    type="number"
                    min="1"
                    max="2147483647"
                    required
                    value={line.qty}
                    onChange={(e) => editLine(i, 'qty', e.target.value)}
                  />
                </Field>
                <button
                  type="button"
                  className="button"
                  aria-label={'Remove item ' + (i + 1)}
                  disabled={lines.length === 1 || line.product_id === requiredId}
                  onClick={() => setLines(lines.filter((_, j) => i !== j))}
                >
                  Remove
                </button>
              </div>
            ))}
            {errors.items && <p className="form-error">{errors.items}</p>}
            <button
              type="button"
              className="button"
              disabled={lines.length >= catalog.length}
              onClick={() => setLines([...lines, { product_id: '', qty: 1 }])}
            >
              Add item
            </button>
          </fieldset>
          {type && !install && (
            <p className="form-error">
              Add the installation service product to the catalog before creating a system package.
            </p>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="actions">
            <button className="button primary" disabled={busy || !!(type && !install)}>
              {busy ? 'Saving…' : initial ? 'Save package' : 'Create package'}
            </button>
            {onCancel && (
              <button type="button" className="button" disabled={busy} onClick={onCancel}>
                Cancel
              </button>
            )}
          </div>
        </form>
      ) : (
        <p className="state">Add a product to the catalog before building a package.</p>
      )}
    </State>
  )
}
