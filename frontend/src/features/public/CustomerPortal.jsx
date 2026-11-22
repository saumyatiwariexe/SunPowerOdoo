import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import PublicFrame from './PublicFrame'
import { api, formatPaise } from '../../app/api'
import { DataTable, Facts, Status } from '../../app/records'
import Field from '../../app/components/Field'
import { human } from '../../app/navigation'

const date = (value) => value ? new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'To be scheduled'

export default function CustomerPortal() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('projects')
  const load = async () => {
    setLoading(true); setError('')
    try { setData((await api.get('/customer/overview')).data) }
    catch (err) { if (err.status === 401) setData(null); else setError(err.message) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  return <PublicFrame><section className="customer-portal">
    <div className="heading"><div><h1>My solar</h1><p className="section-help">Your installation, paperwork and support in one place.</p></div>
      {data && <button className="button" onClick={async () => { try { await api.post('/customer/auth/logout', {}); setData(null) } catch (err) { setError(err.message) } }}>Sign out</button>}
    </div>
    {loading ? <p role="status" className="state">Loading your account…</p> : error ? <div role="alert" className="state error">{error} <button className="button" onClick={load}>Retry</button></div> : !data ? <CustomerLogin onDone={load} /> : <>
      <nav className="view-tabs customer-tabs" aria-label="Customer account sections">
        {['projects', 'documents', 'equipment', 'support'].map((key) => <button key={key} aria-pressed={tab === key} onClick={() => setTab(key)}>{human(key)}</button>)}
      </nav>
      <p className="customer-limit">Showing your latest 50 projects, documents and requests, and up to 100 equipment units.</p>
      {tab === 'projects' && <div className="customer-sections">
        <section><h2>Your enquiries</h2>{!data.projects.length && <p className="state">No enquiries are linked to your account yet. <Link to="/enquiry">Request a quote</Link>.</p>}
          {data.projects.map((project) => <article className="customer-project" key={project.id}>
            <div className="section-line"><h3>{project.requested_kw} kW solar enquiry</h3><Status value={project.status} /></div>
            <p>Reference LEAD-{String(project.id).padStart(4, '0')}</p>
            <p>{project.survey ? `Site survey: ${human(project.survey.status)} · ${date(project.survey.scheduled_at)}` : 'Our sales team will contact you to arrange the next step.'}</p>
          </article>)}
        </section>
        <section><h2>Your installations</h2>{!data.orders.length && <p className="state">Your order and installation schedule will appear after your quote is accepted.</p>}
          {data.orders.map((order) => <article className="customer-project" key={order.id}>
            <div className="section-line"><h3>{order.number}</h3><Status value={order.status} /></div>
            <Facts items={[
              ['Order total', formatPaise(order.total_paise)],
              ['Delivery', order.delivery ? human(order.delivery.status) : 'Awaiting confirmation'],
              ['Installation', order.installation ? human(order.installation.status) : 'Awaiting scheduling'],
              ['Visit starts', date(order.installation?.scheduled_start)],
              ['Visit ends', date(order.installation?.scheduled_end)],
              ['System size', order.installation?.system_kw ? `${order.installation.system_kw} kW` : 'Pending'],
              ['Accepted by', order.installation?.signed_by_name || 'Pending'],
            ]} />
            {order.installation?.accepted_at && <button className="button no-print" onClick={() => window.print()}>Print installation summary</button>}
          </article>)}
        </section>
      </div>}
      {tab === 'documents' && <div className="customer-sections">
        <section><h2>Quotes</h2><DataTable rows={data.quotes} columns={[
          ['number', 'Quote', r => <Link className="text-link" to={`/customer/documents/quotes/${r.id}`}>{r.number}</Link>], ['status', 'Status'], ['total_paise', 'Total'], ['valid_until', 'Valid until'],
        ]} empty="Your issued quotes will appear here." /></section>
        <section><h2>Invoices & payments</h2><DataTable rows={data.invoices} columns={[
          ['number', 'Invoice', r => <Link className="text-link" to={`/customer/documents/invoices/${r.id}`}>{r.number}</Link>], ['status', 'Status'], ['total_paise', 'Total'], ['paid_paise', 'Paid'],
          ['balance', 'Balance', r => formatPaise(Math.max(0, r.total_paise - r.paid_paise))],
        ]} empty="No invoices have been issued yet." /></section>
      </div>}
      {tab === 'equipment' && <section><h2>Equipment & warranty</h2><DataTable rows={data.equipment} columns={[
        ['product_name', 'Equipment'], ['serial_no', 'Serial number'], ['warranty_start', 'Coverage starts'], ['warranty_end', 'Coverage ends'], ['covered', 'Current coverage', r => r.covered ? 'Covered' : 'Not covered'],
      ]} empty="Your serial numbers and warranties appear after delivery." /></section>}
      {tab === 'support' && <div className="customer-sections"><ServiceForm equipment={data.equipment} onDone={load} />
        <section><h2>Your service requests</h2><DataTable rows={data.tickets} columns={[
          ['number', 'Reference'], ['description', 'Issue'], ['status', 'Status'], ['resolution', 'Resolution'], ['billable', 'Charges', r => r.billable ? 'Parts and labour may be charged' : 'Warranty covered'],
        ]} empty="You have no service requests." /></section></div>}
    </>}
  </section></PublicFrame>
}

function CustomerLogin({ onDone }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      await api.post('/customer/auth/login', Object.fromEntries(new FormData(event.currentTarget)))
      onDone()
    } catch (err) { setError(err.details?.[0]?.message || err.message) } finally { setBusy(false) }
  }
  return <section className="customer-login"><h2>Welcome back</h2><p>Use the email and password sent by your SunPower agent.</p>
    <form className="stack" onSubmit={submit}>
      <Field label="Email"><input name="email" type="email" autoComplete="username" required maxLength={254} /></Field>
      <Field label="Password"><input name="password" type="password" autoComplete="current-password" required maxLength={72} /></Field>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button primary" disabled={busy}>{busy ? 'Signing in...' : 'Sign in'}</button>
    </form>
    <p>New customer? Your agent will email your login details after discussing your enquiry. Sign in within 24 hours; no password setup is needed. If the initial login has expired, ask your agent to resend it.</p>
    <p>Need help with access? Contact your SunPower agent.</p>
  </section>
}

export function CustomerActivation() {
  const navigate = useNavigate()
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token') || '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { window.history.replaceState(null, '', window.location.pathname + window.location.search) }, [])
  async function submit(event) {
    event.preventDefault(); setError('')
    const values = Object.fromEntries(new FormData(event.currentTarget))
    if (values.password !== values.confirm) { setError('Passwords do not match.'); return }
    setBusy(true)
    try {
      await api.post('/customer/auth/activate', { token, password: values.password })
      navigate('/customer', { replace: true })
    } catch (err) { setError(err.details?.[0]?.message || err.message) } finally { setBusy(false) }
  }
  return <PublicFrame><section className="customer-portal"><h1>Welcome to My solar</h1>
    <section className="customer-login"><h2>Set your password</h2><p>Track your installation, paperwork and support with your own customer account.</p>
      {!token ? <p role="alert">Open the invitation link from your email. If it has expired, ask your agent to resend it.</p> : <form className="stack" onSubmit={submit}>
        <Field label="New password" hint="Use at least 10 characters"><input name="password" type="password" autoComplete="new-password" required minLength={10} maxLength={72} /></Field>
        <Field label="Confirm password"><input name="confirm" type="password" autoComplete="new-password" required minLength={10} maxLength={72} /></Field>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="button primary" disabled={busy}>{busy ? 'Activating...' : 'Activate my account'}</button>
      </form>}
      <Link className="text-link" to="/customer">Already activated? Sign in</Link>
    </section>
  </section></PublicFrame>
}

function ServiceForm({ equipment, onDone }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState('')
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError(''); const form = event.currentTarget
    try {
      const values = Object.fromEntries(new FormData(form))
      const result = await api.post('/customer/tickets', values)
      setSuccess(`Request ${result.data.number} created. Our support team will follow up.`); form.reset()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <section className="customer-login"><h2>Request service</h2>{!equipment.length ? <p>Equipment must be delivered before you can open a service request. Contact the sales team for enquiry updates.</p> : <form className="stack" onSubmit={submit}>
    <Field label="Equipment"><select name="serial_no" required><option value="">Select your equipment</option>{equipment.map(r => <option key={r.serial_no} value={r.serial_no}>{r.product_name} · {r.serial_no}</option>)}</select></Field>
    <Field label="What is the issue?"><textarea name="description" minLength={10} maxLength={2000} required rows={4} /></Field>
    {error && <p role="alert" className="form-error">{error}</p>}
    {success && <p role="status">{success} <button type="button" className="text-link" onClick={onDone}>Refresh requests</button></p>}
    <button className="button primary" disabled={busy}>{busy ? 'Submitting…' : 'Submit service request'}</button>
  </form>}</section>
}

export function CustomerDocument() {
  const { kind, id } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { setData(null); setError(''); api.get(`/customer/documents/${kind}/${id}`).then(r => setData(r.data)).catch(e => setError(e.message)) }, [kind, id])
  return <PublicFrame><section className="customer-portal customer-document">
    <Link className="back no-print" to="/customer">← My solar</Link>
    {error ? <p role="alert" className="state error">{error} <Link to="/customer">Return to your account</Link></p> : !data ? <p role="status">Loading document…</p> : <>
      <div className="heading"><h1>{data.number}</h1><button className="button primary no-print" onClick={() => window.print()}>Print / save PDF</button></div>
      <Facts items={[
        ['Customer', data.customer?.name], ['Address', data.customer?.address], ['Status', human(data.status)],
        ['Total', formatPaise(data.total_paise)], ...(data.paid_paise != null ? [['Paid', formatPaise(data.paid_paise)], ['Balance', formatPaise(data.balance_paise)]] : [['Valid until', data.valid_until]]),
      ]} />
      <DataTable rows={data.lines} columns={[[ 'description', 'Description'], ['qty', 'Quantity'], ['unit_price_paise', 'Unit price'], ['line_paise', 'Amount']]} />
      {data.subsidy_paise > 0 && <p>Subsidy adjustment: {formatPaise(data.subsidy_paise)}</p>}
    </>}
  </section></PublicFrame>
}
