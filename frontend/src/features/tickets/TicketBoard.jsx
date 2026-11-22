import React, { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import AppIcon from '../../app/AppIcon'
import { useAuth } from '../../app/AuthContext'
import { api } from '../../app/api'
import { DataTable, Heading, Pager, State, useRecord } from '../../app/records'
import { human } from '../../app/navigation'
import Modal from '../../app/components/Modal'
import EquipmentSearch from '../lookup/EquipmentSearch'
import ActionForm from '../../app/ActionForm'
import TicketDetail, { priorities } from './TicketDetail'

const stages = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']

function Queue({ status, query, board, openTicket }) {
  const [page, setPage] = useState(1)
  const params = new URLSearchParams(query)
  if (status) params.set('status', status)
  params.set('page', page)
  params.set('page_size', board ? '6' : '12')
  const resource = useRecord('/tickets?' + params)
  const rows = resource.data || []
  if (!board)
    return (
      <State resource={resource}>
        <DataTable
          rows={rows}
          empty="No tickets match this view."
          columns={[
            [
              'number',
              'Ticket',
              (t) => (
                <button className="text-link" onClick={() => openTicket(t.id)}>
                  {t.number}
                </button>
              ),
            ],
            ['description', 'Issue', t => <div className="ticket-list-issue"><strong>{t.description}</strong><small>{t.customer_name}</small></div>],
            ['priority', 'Priority', (t) => human(t.priority)],
            ['status', 'Status'],
            ['assigned_to_id', 'Assignee', (t) => assignee(t)],
          ]}
        />
        <Pager meta={resource.meta} page={page} setPage={setPage} />
      </State>
    )
  return (
    <section className="lane" aria-label={human(status)}>
      <header>
        <i className={'dot ' + status} />
        <h2>{human(status)}</h2>
        <span>{resource.meta?.total ?? '–'}</span>
      </header>
      <State resource={resource}>
        {rows.map((t) => (
          <button className="ticket-card" key={t.id} onClick={() => openTicket(t.id)}>
            <span className="ticket-key">
              <AppIcon name="ticket" size={15} />
              {t.number}
            </span>
            <strong>{t.description}</strong>
            <small>{t.customer_name} · {t.serial_no}</small>
            <span className="ticket-meta">
              <span className={'priority ' + t.priority}>{human(t.priority)}</span>
              <span>{assignee(t)}</span>
            </span>
          </button>
        ))}
        {!rows.length && <div className="empty-lane">{params.get('mine') ? 'No tickets assigned to you in this stage.' : 'No tickets in this stage.'}</div>}
        <Pager meta={resource.meta} page={page} setPage={setPage} />
      </State>
    </section>
  )
}
const assignee = (t) => t.assigned_to_name || (t.assigned_to_id ? 'Staff #' + t.assigned_to_id : 'Unassigned')

export default function TicketBoard() {
  const { currentUser } = useAuth()
  const [params, setParams] = useSearchParams()
  const [revision, setRevision] = useState(0)
  const [search, setSearch] = useState(params.get('q') || '')
  const board = params.get('view') === 'board'
  const selectedStatus = stages.includes(params.get('status')) ? params.get('status') : params.get('status') === 'ALL' ? '' : 'OPEN'
  const mine = params.get('mine') === '1'
  function set(values, replace = false) {
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(values)) value ? next.set(key, value) : next.delete(key)
    setParams(next, { replace })
  }
  const query = new URLSearchParams()
  if (params.get('q')) query.set('q', params.get('q'))
  if (mine) query.set('mine', 'true')
  const openTicket = (id) => set({ ticket: id, new: null, serial: null })
  return (
    <div className="ticket-workspace">
      <Heading title="Service tickets">
        <Link to="/lookup" className="button">
          <AppIcon name="search" size={16} />
          Serial lookup
        </Link>
        <button className="button primary" onClick={() => set({ new: 1, ticket: null, serial: null })}>
          ＋ Create ticket
        </button>
      </Heading>
      <div className="ticket-toolbar">
        <form
          className="search-box"
          role="search"
          onSubmit={(e) => {
            e.preventDefault()
            set({ q: search.trim() })
          }}
        >
          <AppIcon name="search" size={17} />
          <input
            aria-label="Search tickets by number, customer, serial or issue"
            maxLength="100"
            type="search"
            placeholder="Search ticket, customer or serial"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              if (!e.target.value) set({ q: null }, true)
            }}
          />
          <button aria-label="Apply ticket search">↵</button>
        </form>
        <button className="filter" aria-pressed={mine} onClick={() => set({ mine: mine ? null : 1 })}>
          <AppIcon name="people" size={16} />
          Assigned to me
        </button>
        {!board && <select aria-label="Ticket status" value={selectedStatus || 'ALL'} onChange={e => set({ status: e.target.value })}>
          {stages.map(status => <option key={status} value={status}>{human(status)}</option>)}
          <option value="ALL">All statuses</option>
        </select>}
      <div className="view-tabs ticket-view-switch">
        {[
          ['board', 'board', 'Board'],
          ['list', 'list', 'Queue'],
        ].map(([mode, icon, label]) => (
          <button
            key={mode}
            aria-pressed={(board ? 'board' : 'list') === mode}
            onClick={() => set({ view: mode })}
          >
            <AppIcon name={icon} size={16} />
            {label}
          </button>
        ))}
      </div>
        {params.get('q') && (
          <button
            className="text-link"
            onClick={() => {
              setSearch('')
              set({ q: null })
            }}
          >
            Clear search
          </button>
        )}
      </div>
      {mine && <p className="ticket-filter-note" role="status">Assigned to {currentUser.name}</p>}
      <div className={board ? 'board' : 'ticket-queue'}>
        {(board ? stages : [selectedStatus]).map((status) => (
          <Queue
            key={[status, query, revision].join('/')}
            status={status}
            query={query.toString()}
            board={board}
            openTicket={openTicket}
          />
        ))}
      </div>
      {params.get('new') && (
        <Modal title="Create ticket" onClose={() => set({ new: null, serial: null })}>
          {!params.get('serial') ? <EquipmentSearch assignedOnly onSelect={r => set({ serial: r.serial_no })} /> : <>
          <p>Equipment: <strong>{params.get('serial')}</strong> <button type="button" className="text-link" onClick={() => set({ serial: null })}>Change equipment</button></p>
          <ActionForm
            primary
            submit="Create ticket"
            initial={{ serial_no: params.get('serial') || '', assigned_to_id: mine ? currentUser.id : undefined }}
            fields={[
              { name: 'serial_no', label: 'Equipment serial number', maxLength: 100 },
              { name: 'fault_code', label: 'Issue category', options: ['NO_POWER', 'LOW_GENERATION', 'INVERTER_FAULT', 'BATTERY_FAULT', 'WIRING', 'MONITORING', 'OTHER'] },
              { name: 'description', label: 'Issue description', type: 'textarea', maxLength: 2000 },
              { name: 'priority', label: 'Priority', options: priorities, value: 'NORMAL' },
              { name: 'assigned_to_id', label: 'Assigned staff', lookup: 'assignees', optional: true, hint: 'Choose who owns this repair, or leave it unassigned.' },
            ]}
            action={(v) => api.post('/tickets', v)}
            onDone={(t) => {
              setRevision((v) => v + 1)
              openTicket(t.id)
            }}
          />
          </>}
        </Modal>
      )}
      {params.get('ticket') && (
        <TicketDetail
          key={params.get('ticket')}
          id={params.get('ticket')}
          onClose={() => set({ ticket: null })}
          onChange={() => setRevision((v) => v + 1)}
        />
      )}
    </div>
  )
}
