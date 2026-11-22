import React, { useState } from 'react'
import { api } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import { hasRole } from '../../app/navigation'
import ActionForm from '../../app/ActionForm'
import { Facts, display } from '../../app/records'
import ScheduleSurveyButton from './ScheduleSurveyButton'
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
  const [status, setStatus] = useState('SCHEDULED')
  const mine = hasRole(currentUser, 'SURVEYOR') && !hasRole(currentUser, 'SALES') && !hasRole(currentUser, 'DIRECTOR')
  return (
    <Collection
      title={mine ? 'My site surveys' : 'Site surveys'}
      key={status}
      path={(mine ? '/surveys/mine' : '/surveys') + (status ? '?status=' + status : '')}
      tools={<label className="field">Survey status<select value={status} onChange={e => setStatus(e.target.value)}><option value="">All surveys</option>{['SCHEDULED', 'SUBMITTED', 'APPROVED', 'REJECTED'].map(s => <option key={s} value={s}>{s}</option>)}</select></label>}
      actions={!mine && <ScheduleSurveyButton />}
      empty="No surveys scheduled."
      columns={[
        ['id', 'Survey', recordLink('/surveys', 'Survey')],
        ['customer_name', 'Customer'], ['site_address', 'Site'],
        ['surveyor_name', 'Surveyor'],
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
              ['Customer', r.customer_name], ['Phone', r.customer_phone], ['Site', r.site_address],
              ['Surveyor', r.surveyor_name || r.surveyor_id],
              ['Visit time', display('scheduled_at', r.scheduled_at)],
              ['Roof direction', r.roof_direction],
              ['Tilt (°)', r.tilt_degrees],
              ['Cable distance (m)', r.cable_distance_m],
              ['Shadow notes', r.shadow_notes],
              ['Review', r.review_note],
            ]}
          />
          <p className="state">{r.status === 'SCHEDULED' ? 'The assigned surveyor can upload photos and fill the site assessment below.' : r.status === 'SUBMITTED' ? 'Awaiting Sales or Director review.' : 'Assessment reviewed. Schedule a new visit from the lead if a rejected survey needs another assessment.'}</p>
          <Photos photos={r.photos} />
          {hasRole(currentUser, 'SURVEYOR') && r.surveyor_id === currentUser.id && r.status === 'SCHEDULED' && (
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
                  { name: 'roof_direction', label: 'Roof direction', options: ['South', 'South-east', 'South-west', 'East', 'West', 'North'] },
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
          {(hasRole(currentUser, 'SALES') || hasRole(currentUser, 'DIRECTOR')) && r.status === 'SUBMITTED' && (
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
