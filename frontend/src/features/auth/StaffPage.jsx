import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, changedFields, formatPaise } from '../../app/api'
import { useAuth } from '../../app/AuthContext'
import { human } from '../../app/navigation'
import ActionForm from '../../app/ActionForm'
import { Collection, RecordDetail } from '../../app/RecordPage'
import { Facts } from '../../app/records'

const fields = [
  { name: 'name', label: 'Staff name', maxLength: 120 },
  { name: 'email', label: 'Work email', type: 'email', maxLength: 254 },
  {
    name: 'role',
    label: 'Role',
    options: ['SALES', 'SURVEYOR', 'WAREHOUSE', 'CREW', 'SUPPORT', 'DIRECTOR'],
  },
  { name: 'phone', label: 'Phone', type: 'tel', optional: true, maxLength: 20 },
  { name: 'hourly_rate_paise', label: 'Hourly rate (₹)', type: 'money', value: '0.00' },
  { name: 'active', label: 'Account status', options: ['Active', 'Inactive'] },
]

function staffPayload(values) {
  return { ...values, phone: values.phone || null, active: values.active === 'Active' }
}

export function StaffPage() {
  const navigate = useNavigate()
  return (
    <Collection
      title="Staff accounts"
      path="/users"
      empty="No staff accounts found."
      create={{
        label: 'Add staff',
        fields: [
          ...fields,
          {
            name: 'password',
            label: 'Initial password',
            type: 'password',
            autoComplete: 'new-password',
            maxLength: 72,
          },
        ],
        action: (values) => api.post('/users', staffPayload(values)),
        onDone: (row) => navigate('/staff/' + row.id),
      }}
      columns={[
        [
          'name',
          'Name',
          (row) => (
            <Link className="text-link" to={'/staff/' + row.id}>
              {row.name}
            </Link>
          ),
        ],
        ['email', 'Work email'],
        ['role', 'Role', (row) => human(row.role)],
        ['hourly_rate_paise', 'Hourly rate'],
        ['active', 'Status', (row) => (row.active ? 'Active' : 'Inactive')],
      ]}
    />
  )
}

export function StaffDetail() {
  const { currentUser, refetch } = useAuth()
  return (
    <RecordDetail title="Staff accounts" base="/users" backTo="/staff" singular="Staff member">
      {(row, path, reload) => (
        <>
          <h2>{row.name}</h2>
          <Facts
            items={[
              ['Work email', row.email],
              ['Role', human(row.role)],
              ['Hourly rate', formatPaise(row.hourly_rate_paise)],
              ['Account status', row.active ? 'Active' : 'Inactive'],
              ['Phone', row.phone],
            ]}
          />
          <details>
            <summary>Edit staff account</summary>
            <ActionForm
              submit="Save staff account"
              primary
              fields={fields}
              initial={{
                ...row,
                hourly_rate_paise: (row.hourly_rate_paise / 100).toFixed(2),
                active: row.active ? 'Active' : 'Inactive',
              }}
              action={(values) => api.patch(path, changedFields(row, staffPayload(values)))}
              onDone={() => {
                if (row.id === currentUser.id) refetch()
                reload()
              }}
            />
          </details>
        </>
      )}
    </RecordDetail>
  )
}
