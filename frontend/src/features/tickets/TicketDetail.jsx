import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api'
import { DataTable, Facts, State, Status, useRecord } from '../../app/records'
import ActionForm from '../../app/ActionForm'
import Modal from '../../app/components/Modal'
import { human } from '../../app/navigation'
import { useAuth } from '../../app/AuthContext'

export const priorities = ['LOW', 'NORMAL', 'HIGH', 'URGENT']
export default function TicketDetail({ id, onClose, onChange }) {
  const { currentUser } = useAuth()
  const path = '/tickets/' + id
  const ticket = useRecord(path)
  const t = ticket.data
  const [invoice, setInvoice] = useState(null)
  const [tab, setTab] = useState('Overview')
  function refresh(response) {
    if (response?.invoice_id) setInvoice(response.invoice_id)
    ticket.reload()
    onChange()
  }
  return (
    <Modal className="ticket-dialog" title={t?.number || 'Ticket details'} onClose={onClose}>
      <State resource={ticket}>
        {t && (
          <>
            <Status value={t.status} />
            <h3 className="issue-title">{t.description}</h3>
            <div className="view-tabs">
              {(t.status === 'CLOSED' ? ['Overview', 'Parts & labour'] : ['Overview', 'Edit', 'Parts & labour']).map((x) => (
                <button key={x} aria-pressed={tab === x} onClick={() => setTab(x)}>
                  {x}
                </button>
              ))}
            </div>
            {tab === 'Overview' ? (
              <div className="stack">
                <Facts
                  items={[
                    ['Fault code', t.fault_code],
                    ['Priority', human(t.priority)],
                    ['Customer', t.customer_name || 'Customer #' + t.customer_id],
                    ['Phone', t.customer_phone], ['Equipment serial', t.serial_no],
                    ['Assigned to', t.assigned_to_name || (t.assigned_to_id ? 'Staff #' + t.assigned_to_id : 'Unassigned')],
                    ['Service charge', t.billable ? 'Billable' : 'Covered by warranty'],
                    ['Confirmation', t.customer_confirmed_at ? 'Customer confirmed' : 'Pending'],
                  ]}
                />
                {t.resolution && (
                  <p>
                    <strong>Resolution</strong>
                    <br />
                    {t.resolution}
                  </p>
                )}
                {invoice && (
                  <Link className="text-link" to={'/invoices/' + invoice}>
                    Open invoice #{invoice} →
                  </Link>
                )}
                {t.status !== 'CLOSED' && t.assigned_to_id !== currentUser.id && <ActionForm
                  submit="Assign to me" action={() => api.patch(path, { assigned_to_id: currentUser.id })} onDone={refresh} />}
                {t.status === 'OPEN' && (
                  <ActionForm
                    primary
                    submit="Start work"
                    action={() => api.patch(path, { status: 'IN_PROGRESS' })}
                    onDone={refresh}
                  />
                )}
                {t.status === 'IN_PROGRESS' && (
                  <ActionForm
                    primary
                    submit="Resolve ticket"
                    fields={[
                      { name: 'resolution', label: 'Resolution', type: 'textarea', maxLength: 2000 },
                    ]}
                    action={(v) => api.post(path + '/resolve', v)}
                    onDone={refresh}
                  />
                )}
                {t.status === 'RESOLVED' &&
                  (t.customer_confirmed_at ? (
                    <ActionForm
                      primary
                      submit="Close ticket"
                      action={() => api.post(path + '/close')}
                      onDone={refresh}
                    />
                  ) : (
                    <ActionForm
                      primary
                      submit="Record customer confirmation"
                      action={() => api.post(path + '/confirm')}
                      onDone={refresh}
                    />
                  ))}
              </div>
            ) : tab === 'Edit' ? (
              <div className="stack">
                {['OPEN', 'IN_PROGRESS'].includes(t.status) && <section className="ticket-edit-section">
                  <h3>Edit issue details</h3>
                  <ActionForm key={t.id + ':' + t.description} submit="Save issue details"
                    initial={{ description: t.description, fault_code: t.fault_code }}
                    fields={[{ name: 'description', label: 'Issue description', type: 'textarea', maxLength: 2000 }, { name: 'fault_code', label: 'Issue category', maxLength: 64 }]}
                    action={values => api.patch(path, values)} onDone={refresh} />
                </section>}
                {t.status !== 'CLOSED' && (
                  <section className="ticket-edit-section">
                    <h3>Edit assignment and priority</h3>
                    <ActionForm
                      key={`${t.assigned_to_id}:${t.priority}`}
                      submit="Save changes"
                      initial={{ priority: t.priority, assigned_to_id: t.assigned_to_id }}
                      fields={[
                        {
                          name: 'assigned_to_id',
                          label: 'Assigned staff',
                          lookup: 'assignees',
                          optional: true,
                        },
                        { name: 'priority', label: 'Priority', options: priorities },
                      ]}
                      action={(v) => api.patch(path, { ...v, assigned_to_id: v.assigned_to_id || null })}
                      onDone={refresh}
                    />
                  </section>
                )}
              </div>
            ) : (
              <div className="stack">
                <DataTable
                  rows={t.lines}
                  columns={[
                    ['description', 'Item'],
                    ['type', 'Type'],
                    ['qty', 'Qty'],
                    ['unit_price_paise', 'Unit price'],
                  ]}
                  empty="No parts or labour recorded."
                />
                {t.status !== 'CLOSED' && (
                  <ActionForm
                    submit="Add line"
                    fields={[
                      { name: 'type', label: 'Line type', options: ['PART', 'LABOUR'] },
                      { name: 'description', label: 'Description', maxLength: 255 },
                      { name: 'qty', label: 'Quantity', type: 'number', value: 1, min: 1 },
                      { name: 'unit_price_paise', label: 'Unit price (₹)', type: 'money' },
                    ]}
                    action={(v) => api.post(path + '/lines', v)}
                    onDone={refresh}
                  />
                )}
              </div>
            )}
          </>
        )}
      </State>
    </Modal>
  )
}
