import React, { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ActionForm from './ActionForm'
import Modal from './components/Modal'
import { DataTable, Heading, Pager, State, Status, useRecord } from './records'
import { api } from './api'

export function Collection({ title, path, columns, create, empty, tools, actions, children }) {
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const result = useRecord(path + (path.includes('?') ? '&' : '?') + 'page=' + page)
  return (
    <>
      <Heading title={title}>
        {actions}
        {create && (
          <button className="button primary" onClick={() => setOpen(true)}>
            {create.label}
          </button>
        )}
      </Heading>
      {tools && <div className="collection-tools">{tools}</div>}
      <section className="collection-panel" aria-label={title + ' records'}>
      <div className="collection-summary"><strong>{title}</strong><span>{result.meta ? `${result.meta.total} records` : 'Records'}</span></div>
      <State resource={result}>
        <DataTable rows={result.data} columns={columns} empty={empty} />
        <Pager page={page} setPage={setPage} meta={result.meta} />
      </State>
      </section>
      {children}
      {open && (
        <Modal title={create.label} onClose={() => setOpen(false)}>
          <ActionForm
            primary
            fields={create.fields}
            action={create.action}
            submit={create.label}
            onDone={(row) => {
              setOpen(false)
              result.reload()
              create.onDone?.(row)
            }}
          />
        </Modal>
      )}
    </>
  )
}
export function RecordDetail({ title, base, singular, children, print = false, backTo = base }) {
  const { id } = useParams()
  const path = base + '/' + id
  const result = useRecord(path)
  return (
    <>
      <Link className="back no-print" to={backTo}>
        ← {title}
      </Link>
      <State resource={result}>
        {result.data && (
          <>
            <Heading title={result.data.number || singular + ' #' + id}>
              {print && (
                <button className="button" onClick={() => window.print()}>
                  Print {singular.toLowerCase()}
                </button>
              )}
            </Heading>
            {result.data.status && <Status value={result.data.status} />}
            <div className="detail-stack">{children(result.data, path, result.reload)}</div>
          </>
        )}
      </State>
    </>
  )
}
export const recordLink = (base, label) => (row) => (
  <Link className="text-link" to={base + '/' + row.id}>
    {row.number || label + ' #' + row.id}
  </Link>
)
export function imageUpload(path, values) {
  const body = new FormData()
  for (const [key, value] of Object.entries(values)) body.append(key, value)
  return api.upload(path, body)
}
export function Photos({ photos = [] }) {
  return (
    photos.length > 0 && (
      <div className="photo-strip">
        {photos.map((photo) => (
          <a key={photo.id} href={photo.url} target="_blank" rel="noreferrer">
            <img src={photo.url} alt={photo.caption || 'Site photo ' + photo.id} />
          </a>
        ))}
      </div>
    )
  )
}
export const photoField = {
  name: 'file',
  label: 'Site photo',
  type: 'file',
  accept: 'image/jpeg,image/png,image/webp',
}
export const moneyLines = [
  ['description', 'Description'],
  ['qty', 'Qty'],
  ['unit_price_paise', 'Unit price'],
  ['line_paise', 'Amount'],
]
