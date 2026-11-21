import React, { useCallback, useEffect, useState } from 'react'
import { api, formatPaise } from './api'
import { human } from './navigation'

export function useRecord(path) {
  const [version, setVersion] = useState(0)
  const [result, setResult] = useState({})
  useEffect(() => {
    if (!path) return
    let current = true
    api
      .get(path)
      .then((response) => {
        if (current) setResult({ path, version, ...response })
      })
      .catch((err) => {
        if (current) setResult({ path, version, error: err.message })
      })
    return () => {
      current = false
    }
  }, [path, version])
  const reload = useCallback(() => setVersion((v) => v + 1), [])
  return {
    ...(result.path === path && result.version === version ? result : { loading: !!path }),
    reload,
  }
}
export function State({ resource, children }) {
  if (resource.loading)
    return (
      <p role="status" className="state">
        Loading…
      </p>
    )
  if (resource.error)
    return (
      <div role="alert" className="state error">
        {resource.error}{' '}
        <button className="button" onClick={resource.reload}>
          Try again
        </button>
      </div>
    )
  return children
}
export function Heading({ title, children }) {
  return (
    <header className="heading">
      <h1>{title}</h1>
      <div className="actions no-print">{children}</div>
    </header>
  )
}
export function Status({ value }) {
  return (
    <span className="status" data-status={value}>
      <i />
      {human(value)}
    </span>
  )
}
export function display(key, value) {
  if (value == null || value === '') return '—'
  if (key.endsWith('_paise')) return formatPaise(value)
  if (key === 'status') return <Status value={value} />
  if (key.endsWith('_at') || key.startsWith('scheduled_'))
    return new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value).replaceAll('_', ' ')
}
export function DataTable({ rows = [], columns, empty = 'No records yet.' }) {
  if (!rows.length) return <p className="state">{empty}</p>
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map(([key, title]) => (
              <th key={key} scope="col">
                {title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? i}>
              {columns.map(([key, , render]) => (
                <td key={key}>{render ? render(r) : display(key, r[key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
export function Pager({ meta, page, setPage }) {
  if (!meta?.page_size || meta.total <= meta.page_size) return null
  return (
    <div className="pager">
      <button className="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} of {Math.ceil(meta.total / meta.page_size)}
      </span>
      <button
        className="button"
        disabled={page * meta.page_size >= meta.total}
        onClick={() => setPage(page + 1)}
      >
        Next
      </button>
    </div>
  )
}
export function Facts({ items }) {
  return (
    <dl className="facts">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value ?? '—'}</dd>
        </div>
      ))}
    </dl>
  )
}
