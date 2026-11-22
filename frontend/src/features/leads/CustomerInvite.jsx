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
    {account?.login_url && <p>Customer login: <a className="text-link" href={account.login_url} target="_blank" rel="noreferrer">{account.login_url}</a></p>}
    {error ? <p role="alert">{error} <button className="button" onClick={load}>Retry</button></p> : !account ? <p role="status">Checking portal access...</p> : account.status === 'ACTIVE' ? <p>Account active for <strong>{account.email}</strong>. This customer can sign in to My solar.</p> : <>
      <p>{account.status === 'INVITED' ? `An invitation is pending for ${account.email}. Resending generates a new password and replaces the previous one.` : 'Grant access after discussing the enquiry. The customer receives their email, an automatically generated password and the login address. No password setup is required.'}</p>
      {['NEW', 'LOST'].includes(lead.status) ? <p>Contact this lead before inviting them. Lost leads cannot be onboarded.</p> : <ActionForm
        key={account.email || lead.id}
        fields={[{ name: 'email', label: 'Customer email', type: 'email', maxLength: 254 }]}
        initial={{ email: account.email || lead.customer?.email || '' }}
        submit={account.status === 'INVITED' ? 'Resend login details' : 'Send customer login'}
        action={values => api.post(path + '/invite', values)}
        onDone={() => { setMessage('Login details accepted by SendGrid. Ask the customer to check their inbox and sign in within 24 hours.'); load() }}
      />}
      {message && <p role="status">{message}</p>}
    </>}
  </section>
}
