import React, { useRef } from 'react'
import SignatureField from './SignatureField'
import { api } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
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
  const mine = currentUser.role === 'CREW'
  return (
    <Collection
      title={mine ? 'My installations' : 'Installations'}
      path={mine ? '/installs/mine' : '/installs'}
      empty="No installation jobs yet."
      columns={[
        ['id', 'Job', recordLink('/installs', 'Job')],
        ['order_id', 'Order ID'],
        ['scheduled_start', 'Scheduled start'],
        ['crew_lead_id', 'Crew lead ID'],
        ['status', 'Status'],
      ]}
    />
  )
}
export function InstallDetail() {
  const { currentUser } = useAuth()
  const crew = currentUser.role === 'CREW'
  return (
    <RecordDetail title="Installations" base="/installs" singular="Installation">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Order ID', r.order_id],
              ['Crew', r.crew.map((c) => '#' + c.user_id).join(', ') || 'Unassigned'],
              ['From', display('scheduled_start', r.scheduled_start)],
              ['Until', display('scheduled_end', r.scheduled_end)],
              ['System (kW)', r.system_kw],
              ['Signed by', r.signed_by_name],
              ['Test notes', r.test_notes],
            ]}
          />
          <Photos photos={r.photos} />
          {r.signature_url && (
            <a className="text-link" href={r.signature_url}>
              View customer signature
            </a>
          )}
          {!crew && r.status === 'SCHEDULED' && (
            <ActionForm
              primary
              submit="Save schedule"
              fields={[
                { name: 'crew_lead_id', label: 'Crew lead', lookup: 'crew' },
                { name: 'crew_ids', label: 'Crew members', lookup: 'crew', multiple: true, optional: true },
                { name: 'scheduled_start', label: 'Start', type: 'datetime-local' },
                { name: 'scheduled_end', label: 'End', type: 'datetime-local' },
              ]}
              initial={{ crew_lead_id: r.crew_lead_id, crew_ids: r.crew.map((c) => c.user_id) }}
              action={(v) => api.patch(path + '/schedule', v)}
              onDone={reload}
            />
          )}
          {crew && r.status === 'SCHEDULED' && (
            <ActionForm
              primary
              submit="Start installation"
              action={() => api.post(path + '/start')}
              onDone={reload}
            />
          )}
          {crew && r.status === 'IN_PROGRESS' && (
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
          {crew && r.status === 'COMPLETED' && (
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
