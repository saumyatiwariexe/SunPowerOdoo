import React from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../app/api'
import { Facts, DataTable } from '../../app/records'
import { RecordDetail } from '../../app/RecordPage'
import ActionForm from '../../app/ActionForm'
import CallChecklistForm from './CallChecklistForm'
import ScheduleSurveyButton from '../surveys/ScheduleSurveyButton'

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
