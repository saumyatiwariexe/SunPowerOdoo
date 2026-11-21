import React from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import ActionForm from '../../app/ActionForm'
import { Facts, display } from '../../app/records'
import {
  Collection,
  RecordDetail,
  recordLink,
  Photos,
  imageUpload,
  photoField,
} from '../../app/RecordPage'

export function SurveysPage() {
  const { currentUser } = useAuth()
  const navigate = useNavigate()
  const mine = currentUser.role === 'SURVEYOR'
  const create = {
    label: 'Schedule survey',
    fields: [
      { name: 'lead_id', label: 'Lead ID', type: 'number', min: 1 },
      { name: 'surveyor_id', label: 'Surveyor ID', type: 'number', min: 1 },
      { name: 'scheduled_at', label: 'Visit time', type: 'datetime-local' },
    ],
    action: ({ lead_id, ...v }) => api.post('/leads/' + lead_id + '/survey', v),
    onDone: (r) => navigate('/surveys/' + r.id),
  }
  return (
    <Collection
      title={mine ? 'My site surveys' : 'Site surveys'}
      path={mine ? '/surveys/mine' : '/surveys'}
      create={mine ? null : create}
      empty="No surveys scheduled."
      columns={[
        ['id', 'Survey', recordLink('/surveys', 'Survey')],
        ['lead_id', 'Lead ID'],
        ['surveyor_id', 'Surveyor ID'],
        ['scheduled_at', 'Visit time'],
        ['status', 'Status'],
      ]}
    />
  )
}
export function SurveyDetail() {
  const { currentUser } = useAuth()
  return (
    <RecordDetail title="Site surveys" base="/surveys" singular="Survey">
      {(r, path, reload) => (
        <>
          <Facts
            items={[
              ['Lead ID', r.lead_id],
              ['Surveyor ID', r.surveyor_id],
              ['Visit time', display('scheduled_at', r.scheduled_at)],
              ['Roof direction', r.roof_direction],
              ['Tilt (°)', r.tilt_degrees],
              ['Cable distance (m)', r.cable_distance_m],
              ['Shadow notes', r.shadow_notes],
              ['Review', r.review_note],
            ]}
          />
          <Photos photos={r.photos} />
          {currentUser.role === 'SURVEYOR' && r.status === 'SCHEDULED' && (
            <>
              <ActionForm
                submit="Upload photo"
                fields={[photoField]}
                action={(v) => imageUpload(path + '/photos', v)}
                onDone={reload}
              />
              <ActionForm
                primary
                submit="Submit survey"
                fields={[
                  { name: 'roof_direction', label: 'Roof direction' },
                  {
                    name: 'tilt_degrees',
                    label: 'Tilt (degrees)',
                    type: 'number',
                    step: 'any',
                    min: 0,
                    max: 90,
                  },
                  {
                    name: 'cable_distance_m',
                    label: 'Cable distance (m)',
                    type: 'number',
                    step: 'any',
                    min: 0,
                  },
                  { name: 'shadow_notes', label: 'Shadow notes', type: 'textarea', optional: true },
                ]}
                action={(v) => api.post(path + '/submit', v)}
                onDone={reload}
              />
            </>
          )}
          {currentUser.role !== 'SURVEYOR' && r.status === 'SUBMITTED' && (
            <ActionForm
              primary
              submit="Save review"
              fields={[
                { name: 'decision', label: 'Decision', options: ['approve', 'reject'] },
                { name: 'note', label: 'Review note', type: 'textarea' },
              ]}
              action={({ decision, ...v }) => api.post(path + '/' + decision, v)}
              onDone={reload}
            />
          )}
        </>
      )}
    </RecordDetail>
  )
}
