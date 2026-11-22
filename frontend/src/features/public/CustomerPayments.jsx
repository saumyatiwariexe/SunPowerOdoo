import React, { useEffect, useState } from 'react'
import { api, formatPaise } from '../../app/api'
import ActionForm from '../../app/ActionForm'
import { DataTable, Facts } from '../../app/records'

export default function CustomerPayments({ kind, id, staff = false, onChange }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const base = staff ? '/customer-management' : '/customer'
  const path = `${base}/${kind}/${id}/payment-reports`
  async function load() {
    setError('')
    try { setData((await api.get(path)).data) } catch (e) { setError(e.message) }
  }
  useEffect(() => { setData(null); load() }, [path])
  async function changed(message) { setNotice(message); await load(); onChange?.() }
  return <section className="customer-payment-panel no-print">
    <div className="section-line"><h3>{staff ? 'Customer payment reports' : 'Payment & advance'}</h3><button type="button" className="button" onClick={load}>Refresh</button></div>
    {error && <p role="alert" className="form-error">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {!data ? !error && <p role="status">Loading payments…</p> : <>
      <Facts items={[
        ['Verified payments', formatPaise(data.paid_paise)],
        ['Balance', formatPaise(data.balance_paise)],
        ...(data.advance_min_paise != null ? [['Advance still needed', formatPaise(Math.max(0, data.advance_min_paise - data.paid_paise))]] : []),
        ['Awaiting verification', formatPaise(data.pending_paise)],
      ]} />
      {!staff && <>
        <p>Ask your SunPower agent for the bank or UPI details. After transferring, report the transaction below. Your balance updates after the team verifies receipt.</p>
        {data.reportable_paise > 0 ? <details><summary>I have paid — submit transaction details</summary>
          <ActionForm primary submit="Submit for verification" fields={[
            { name: 'amount_paise', label: 'Amount paid (₹)', type: 'money', min: 0.01 },
            { name: 'method', label: 'Payment method', options: ['UPI', 'BANK'] },
            { name: 'reference', label: 'Transaction / UTR reference', minLength: 3, maxLength: 100 },
          ]} action={v => api.post(path, v)} onDone={() => changed('Payment reported. It is awaiting staff verification.')} />
        </details> : <p>{data.balance_paise === 0 ? 'Paid in full.' : 'Your remaining balance is awaiting verification.'}</p>}
      </>}
      <DataTable rows={data.reports} empty="No customer payment reports yet." columns={[
        ['reference', 'Transaction'], ['amount_paise', 'Amount'], ['method', 'Method'], ['status', 'Status'], ['review_note', 'Team note'],
      ]} />
      {staff && data.reports.filter(r => r.status === 'PENDING').map(r => <details key={r.id}>
        <summary>Review {r.reference} · {formatPaise(r.amount_paise)}</summary>
        <p>Check the actual bank/UPI receipt before verifying. Do not record the same payment again using “Record payment”.</p>
        <ActionForm submit="Save review" fields={[
          { name: 'decision', label: 'Decision', options: ['VERIFIED', 'REJECTED'] },
          { name: 'note', label: 'Verification or rejection note', minLength: 3, maxLength: 500 },
        ]} action={v => api.post(`/customer-management/payment-reports/${r.id}/review`, v)}
          onDone={() => changed('Review saved. Verified receipts are included in the paid balance.')} />
      </details>)}
    </>}
  </section>
}
