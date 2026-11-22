import React, { useRef, useState } from 'react'
import SignatureField from './SignatureField'
import { api } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import { hasRole } from '../../app/navigation'
import ActionForm from '../../app/ActionForm'
import { Facts, display } from '../../app/records'
import {
  Collection,
  RecordDetail,
  recordLink,
  imageUpload,
  Photos,
  photoField,
} from '../../app/RecordPage'

export function InstallsPage() {
  const { currentUser } = useAuth()
  const mine = hasRole(currentUser, 'CREW') && !hasRole(currentUser, 'SUPPORT') && !hasRole(currentUser, 'DIRECTOR')
  const [status, setStatus] = useState(mine ? 'SCHEDULED' : 'NEEDS_SCHEDULE')
  const query = status === 'NEEDS_SCHEDULE' ? '?needs_schedule=true' : status ? '?status=' + status : ''
  return (
    <Collection
      title={mine ? 'My installations' : 'Installations'}
      key={status}
      path={(mine ? '/installs/mine' : '/installs') + query}
      tools={<label className="field">Job status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">All jobs</option>{!mine && <option value="NEEDS_SCHEDULE">Needs crew and visit time</option>}{['SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'ACCEPTED'].map(s => <option key={s} value={s}>{s === 'SCHEDULED' ? 'All scheduled stage' : s.replaceAll('_', ' ')}</option>)}</select></label>}
      empty="No installation jobs yet."
      columns={[
        ['id', 'Job', recordLink('/installs', 'Job')],
        ['customer_name', 'Customer'], ['site_address', 'Site'], ['order_number', 'Order'],
        ['scheduled_start', 'Scheduled start'],
        ['crew_names', 'Crew'],
        ['status', 'Status', row => row.status === 'SCHEDULED' && !row.scheduled_start ? 'Needs scheduling' : row.status],
      ]}
    />
  )
}
export function InstallDetail() {
  const { currentUser } = useAuth()
  const crew = hasRole(currentUser, 'CREW')
  const scheduler = hasRole(currentUser, 'SUPPORT') || hasRole(currentUser, 'DIRECTOR')
  return (
    <RecordDetail title="Installations" base="/installs" singular="Installation">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Customer', r.customer_name], ['Phone', r.customer_phone], ['Site', r.site_address], ['Order', r.order_number || r.order_id],
              ['Crew', r.crew_names || 'Unassigned'],
              ['From', display('scheduled_start', r.scheduled_start)],
              ['Until', display('scheduled_end', r.scheduled_end)],
              ['System (kW)', r.system_kw],
              ['Signed by', r.signed_by_name],
              ['Test notes', r.test_notes],
            ]}
          />
          <p className="state">{r.status === 'SCHEDULED' ? (r.crew.length ? 'Assigned crew: start the installation to record photos, test results and the customer signature.' : 'Support or Director must assign a crew and visit time before work can start.') : r.status === 'IN_PROGRESS' ? 'Required to finish: site photo, finish time, installed kW, customer name and signature.' : r.status === 'COMPLETED' ? 'Proof is saved. Assigned crew must accept the installation to finish the order.' : 'Installation accepted. Completion proof is read-only.'}</p>
          <Photos photos={r.photos} />
          {r.signature_url && (
            <a className="text-link" href={r.signature_url}>
              View customer signature
            </a>
          )}
          {scheduler && r.status === 'SCHEDULED' && (
            <ActionForm
              primary
              submit="Save schedule"
              fields={[
                { name: 'crew_lead_id', label: 'Crew lead', lookup: 'crew' },
                { name: 'crew_ids', label: 'Crew members', lookup: 'crew', multiple: true, optional: true },
                { name: 'scheduled_start', label: 'Start', type: 'datetime-local' },
                { name: 'scheduled_end', label: 'End', type: 'datetime-local' },
              ]}
              initial={{ crew_lead_id: r.crew_lead_id, crew_ids: r.crew.map((c) => c.user_id), scheduled_start: localTime(r.scheduled_start), scheduled_end: localTime(r.scheduled_end) }}
              action={(v) => api.patch(path + '/schedule', v)}
              onDone={reload}
            />
          )}
          {crew && r.crew.some((member) => member.user_id === currentUser.id) && r.status === 'SCHEDULED' && (
            <ActionForm
              primary
              submit="Start installation"
              action={() => api.post(path + '/start')}
              onDone={reload}
            />
          )}
          {crew && r.crew.some((member) => member.user_id === currentUser.id) && r.status === 'IN_PROGRESS' && (
            <>
              <ActionForm
                submit="Upload site photo"
                fields={[photoField]}
                action={(v) => imageUpload(path + '/photos', v)}
                onDone={reload}
              />
              <Completion key={r.id} row={r} path={path} reload={reload} />
            </>
          )}
          {crew && r.crew.some(member => member.user_id === currentUser.id) && r.status === 'COMPLETED' && (
            <ActionForm
              primary
              submit="Accept installation"
              action={() => api.post(path + '/accept')}
              onDone={reload}
            />
          )}
        </>
      )}
    </RecordDetail>
  )
}

function Completion({ row, path, reload }) {
  const signature = useRef(null)
  async function complete(values) {
    if (!values.signature && signature.current) {
      const blob = await new Promise((resolve) => signature.current.toBlob(resolve, 'image/png'))
      if (blob) values.signature = new File([blob], 'signature.png', { type: 'image/png' })
    }
    if (!values.signature) throw new Error('Draw the customer signature or upload a signature image.')
    return imageUpload(path + '/complete', { ...values, started_at: row.started_at })
  }
  return (
    <section className="stack">
      <SignatureField
        onChange={(value) => {
          signature.current = value
        }}
      />
      <ActionForm
        primary
        submit="Complete installation"
        fields={[
          { name: 'finished_at', label: 'Finish time', type: 'datetime-local' },
          {
            name: 'system_kw',
            label: 'Installed capacity (kW)',
            type: 'number',
            min: 0.01,
            step: 'any',
          },
          { name: 'test_notes', label: 'Test notes', type: 'textarea', optional: true },
          { name: 'signed_by_name', label: 'Customer name' },
          {
            name: 'signature',
            label: 'Or upload a signature image',
            type: 'file',
            optional: true,
            accept: photoField.accept,
          },
        ]}
        action={complete}
        onDone={reload}
      />
    </section>
  )
}

function localTime(value) {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
