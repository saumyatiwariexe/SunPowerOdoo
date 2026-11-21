import React, { useEffect, useState } from 'react'
import { api } from '../../app/api'
import ActionForm from '../../app/ActionForm'

export default function CustomerInvite({ lead }) {
  const [account, setAccount] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const path = `/customer-management/leads/${lead.id}`
  const load = () => {
    setError('')
    api.get(path).then(r => setAccount(r.data)).catch(e => setError(e.message))
  }
  useEffect(load, [path])
  return <section className="customer-onboarding">
    <h2>Customer portal access</h2>
    {error ? <p role="alert">{error} <button className="button" onClick={load}>Retry</button></p> : !account ? <p role="status">Checking portal access...</p> : account.status === 'ACTIVE' ? <p>Account active for <strong>{account.email}</strong>. This customer can sign in to My solar.</p> : <>
      <p>{account.status === 'INVITED' ? `An invitation is pending for ${account.email}. Resending replaces the previous link.` : 'Grant access after discussing the enquiry. The customer receives a one-time email link to set their password.'}</p>
      {['NEW', 'LOST'].includes(lead.status) ? <p>Contact this lead before inviting them. Lost leads cannot be onboarded.</p> : <ActionForm
        key={account.email || lead.id}
        fields={[{ name: 'email', label: 'Customer email', type: 'email', maxLength: 254 }]}
        initial={{ email: account.email || lead.customer?.email || '' }}
        submit={account.status === 'INVITED' ? 'Resend invitation' : 'Invite customer'}
        action={values => api.post(path + '/invite', values)}
        onDone={() => { setMessage('Invitation accepted by SendGrid. Ask the customer to check their inbox.'); load() }}
      />}
      {message && <p role="status">{message}</p>}
    </>}
  </section>
}
