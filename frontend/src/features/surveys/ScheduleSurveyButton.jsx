import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ActionForm from '../../app/ActionForm'
import { api } from '../../app/api'
import Modal from '../../app/components/Modal'
import { State, useRecord } from '../../app/records'

function ScheduleSurveyForm({ leadId, onDone }) {
  const options = useRecord('/surveys/scheduling-options' + (leadId ? '?lead_id=' + leadId : ''))
  const { leads = [], surveyors = [], existing_survey_id: existing } = options.data || {}
  let content
  if (existing) {
    content = <Link to={'/surveys/' + existing}>View this lead’s existing survey</Link>
  } else if (!leads.length) {
    content = <p>No leads are ready to schedule here. Open the <Link to="/leads">lead inbox</Link> and log the first customer call on a new lead.</p>
  } else if (!surveyors.length) {
    content = <p>No active surveyors are available. A director can add or activate a surveyor in Staff.</p>
  } else {
    content = (
      <ActionForm
        primary
        submit="Schedule survey"
        fields={[
          {
            name: 'lead_id', label: 'Lead', value: leadId || '', placeholder: 'Choose a contacted lead',
            options: leads.map((lead) => ({ value: lead.id, label: lead.name + ' · Lead #' + lead.id })),
          },
          {
            name: 'surveyor_id', label: 'Surveyor', placeholder: 'Choose a surveyor',
            options: surveyors.map((user) => ({ value: user.id, label: user.name + ' · #' + user.id })),
          },
          { name: 'scheduled_at', label: 'Visit time', type: 'datetime-local' },
        ]}
        action={({ lead_id, surveyor_id, scheduled_at }) =>
          api.post('/leads/' + lead_id + '/survey', { surveyor_id: Number(surveyor_id), scheduled_at })
        }
        onDone={onDone}
      />
    )
  }
  return <State resource={options}>{content}</State>
}

export default function ScheduleSurveyButton({ leadId }) {
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  return (
    <>
      <button className="button primary" onClick={() => setOpen(true)}>Schedule survey</button>
      {open && (
        <Modal title="Schedule survey" onClose={() => setOpen(false)}>
          <ScheduleSurveyForm leadId={leadId} onDone={(survey) => navigate('/surveys/' + survey.id)} />
        </Modal>
      )}
    </>
  )
}
