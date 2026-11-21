import React from 'react'
import Modal from '../../app/components/Modal'
import ActionForm from '../../app/ActionForm'
import { api } from '../../app/api'
export default function NewLeadModal({ onClose, onCreated }) {
  return (
    <Modal title="New lead" onClose={onClose}>
      <ActionForm
        primary
        submit="Create lead"
        fields={[
          { name: 'name', label: 'Customer name', maxLength: 120 },
          { name: 'phone', label: 'Mobile number', type: 'tel', maxLength: 10 },
          { name: 'address', label: 'Installation address' },
          { name: 'pincode', label: 'Pincode', maxLength: 6 },
          { name: 'source', label: 'Source', options: ['CALL', 'WHATSAPP', 'WEB'] },
          {
            name: 'requested_kw',
            label: 'Requested capacity (kW)',
            type: 'number',
            min: 0.1,
            max: 100,
            step: 'any',
          },
          { name: 'system_type', label: 'System type', options: ['ON_GRID', 'OFF_GRID'] },
          { name: 'interest', label: 'Interested in subsidy', options: ['No', 'Yes'] },
          { name: 'notes', label: 'Notes', type: 'textarea', optional: true },
        ]}
        action={({ interest, ...v }) =>
          api.post('/leads', { ...v, subsidy_interest: interest === 'Yes' })
        }
        onDone={onCreated}
      />
    </Modal>
  )
}
