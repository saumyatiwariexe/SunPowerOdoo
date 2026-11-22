import React from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api'
import { Facts, DataTable } from '../../app/records'
import { RecordDetail } from '../../app/RecordPage'
import ActionForm from '../../app/ActionForm'
import CallChecklistForm from './CallChecklistForm'
import ScheduleSurveyButton from '../surveys/ScheduleSurveyButton'
import CustomerInvite from './CustomerInvite'

export default function LeadDetailPage() {
  return (
    <RecordDetail title="Lead inbox" base="/leads" singular="Lead">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Customer', r.customer?.name || 'Customer #' + r.customer_id],
              ['Phone', r.customer?.phone],
              ['Address', r.customer?.address],
              ['System', r.system_type.replace('_', '-')],
              ['Capacity', r.requested_kw + ' kW'],
              ['Source', r.source],
              ['Subsidy interest', r.subsidy_interest ? 'Yes' : 'No'],
            ]}
          />
          {!['WON', 'LOST'].includes(r.status) && <details open>
            <summary>Edit enquiry requirements</summary>
            <ActionForm submit="Save requirements" initial={{ requested_kw: r.requested_kw, system_type: r.system_type, notes: r.notes || '' }}
              fields={[{ name: 'requested_kw', label: 'Required capacity (kW)', type: 'number', min: 0.1, max: 100, step: 0.1 }, { name: 'system_type', label: 'System type', options: ['ON_GRID', 'OFF_GRID'] }, { name: 'notes', label: 'Site requirements / follow-up notes', type: 'textarea', optional: true }]}
              action={values => api.patch(path, values)} onDone={reload} />
          </details>}
          {r.lost_reason && <p>Reason for loss: {r.lost_reason}</p>}
          {!['LOST', 'WON'].includes(r.status) && (
            <>
              <details open={r.status === 'NEW'}>
                <summary>Log customer call</summary>
                <CallChecklistForm lead={r} onCallLogged={reload} />
              </details>
              {['CONTACTED', 'SURVEY_PENDING'].includes(r.status) && (
                <ScheduleSurveyButton leadId={r.id} />
              )}
              {r.status === 'SURVEY_DONE' && (
                <Link className="text-link" to="/quotes">
                  Create a quote →
                </Link>
              )}
              <details>
                <summary>Mark lead as lost</summary>
                <ActionForm
                  submit="Mark as lost"
                  fields={[{ name: 'lost_reason', label: 'Reason for loss', type: 'textarea' }]}
                  action={(v) => api.post(path + '/lost', v)}
                  onDone={reload}
                />
              </details>
            </>
          )}
          <CustomerInvite lead={r} />
          <h2>Call history</h2>
          <DataTable
            rows={r.calls}
            columns={[
              ['called_at', 'Called'],
              ['outcome', 'Outcome'],
              ['notes', 'Notes'],
              ['monthly_bill_paise', 'Monthly bill'],
            ]}
            empty="No calls logged."
          />
        </>
      )}
    </RecordDetail>
  )
}
