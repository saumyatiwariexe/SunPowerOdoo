import React, { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../../app/api.js'
import Field, { inputCls, selectCls, textareaCls } from '../../app/components/Field.jsx'
import Spinner from '../../app/components/Spinner.jsx'

const KW_OPTIONS = ['1', '2', '3', '4', '5']
const SYSTEM_TYPES = [
  { value: 'ON_GRID',  label: 'On-Grid (Grid-tied)' },
  { value: 'OFF_GRID', label: 'Off-Grid (Battery backup)' },
]

export default function EnquiryForm() {
  const navigate = useNavigate()
  const [params] = useSearchParams()

  const [form, setForm] = useState({
    name:              '',
    phone:             '',
    address:           '',
    pincode:           '',
    requested_kw:      params.get('kw') || '3',
    system_type:       params.get('type') || 'ON_GRID',
    subsidy_interest:  params.get('subsidy') === 'true',
    monthly_bill:      '',
    // honeypot — must remain empty
    _honey:            '',
  })
  const [errors,  setErrors]  = useState({})
  const [loading, setLoading] = useState(false)
  const [serverErr, setServerErr] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.name.trim())    e.name    = 'Full name is required'
    if (!form.phone.trim())   e.phone   = 'Phone number is required'
    else if (!/^[6-9]\d{9}$/.test(form.phone.trim())) e.phone = 'Enter a valid 10-digit Indian mobile number'
    if (!form.address.trim()) e.address  = 'Address is required'
    if (!form.pincode.trim()) e.pincode  = 'Pincode is required'
    else if (!/^\d{6}$/.test(form.pincode.trim()))    e.pincode = 'Enter a valid 6-digit pincode'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    // Honeypot check
    if (form._honey) return
    if (!validate()) return

    setLoading(true)
    setServerErr('')
    try {
      const payload = {
        name:            form.name.trim(),
        phone:           form.phone.trim(),
        address:         form.address.trim(),
        pincode:         form.pincode.trim(),
        requested_kw:    parseFloat(form.requested_kw),
        system_type:     form.system_type,
        subsidy_interest: form.subsidy_interest,
        monthly_bill_paise: form.monthly_bill
          ? Math.round(parseFloat(form.monthly_bill) * 100)
          : null,
      }
      const { data } = await api.post('/public/enquiries', payload)
      navigate('/thank-you', { state: { reference: data?.reference_no || data?.id } })
    } catch (err) {
      if (err.details?.length) {
        const fieldErrs = {}
        err.details.forEach(d => { if (d.field) fieldErrs[d.field] = d.message })
        setErrors(fieldErrs)
      }
      setServerErr(err.message || 'Submission failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 py-10 px-4">
      <div className="mx-auto max-w-xl">
        <Link to="/" className="text-sm text-slate-500 hover:text-amber-600 mb-6 inline-block">← Back to home</Link>

        <div className="bg-white rounded-2xl shadow p-8">
          <div className="text-center mb-8">
            <div className="text-4xl mb-2">☀️</div>
            <h1 className="text-2xl font-bold text-slate-900">Get a Free Solar Quote</h1>
            <p className="text-slate-500 text-sm mt-1">We'll get back to you within 24 hours</p>
          </div>

          {serverErr && (
            <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {serverErr}
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
            {/* Honeypot - visually hidden */}
            <input
              type="text"
              tabIndex={-1}
              autoComplete="off"
              className="absolute left-[-9999px] opacity-0 h-0"
              value={form._honey}
              onChange={e => set('_honey', e.target.value)}
              aria-hidden="true"
            />

            <Field label="Full Name" error={errors.name} required>
              <input
                type="text"
                className={inputCls}
                value={form.name}
                onChange={e => set('name', e.target.value)}
                placeholder="Rajesh Kumar"
                disabled={loading}
              />
            </Field>

            <Field label="Mobile Number" error={errors.phone} required hint="10-digit Indian mobile number">
              <input
                type="tel"
                className={inputCls}
                value={form.phone}
                onChange={e => set('phone', e.target.value)}
                placeholder="9876543210"
                maxLength={10}
                disabled={loading}
              />
            </Field>

            <Field label="Installation Address" error={errors.address} required>
              <textarea
                className={textareaCls}
                rows={3}
                value={form.address}
                onChange={e => set('address', e.target.value)}
                placeholder="Flat/House no, Street, Area, City"
                disabled={loading}
              />
            </Field>

            <Field label="Pincode" error={errors.pincode} required>
              <input
                type="text"
                className={inputCls}
                value={form.pincode}
                onChange={e => set('pincode', e.target.value)}
                placeholder="400001"
                maxLength={6}
                disabled={loading}
              />
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field label="System Size (kW)" error={errors.requested_kw} required>
                <select
                  className={selectCls}
                  value={form.requested_kw}
                  onChange={e => set('requested_kw', e.target.value)}
                  disabled={loading}
                >
                  {KW_OPTIONS.map(k => (
                    <option key={k} value={k}>{k} kW</option>
                  ))}
                </select>
              </Field>

              <Field label="System Type" error={errors.system_type} required>
                <select
                  className={selectCls}
                  value={form.system_type}
                  onChange={e => set('system_type', e.target.value)}
                  disabled={loading}
                >
                  {SYSTEM_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </Field>
            </div>

            <Field label="Monthly Electricity Bill (₹)" error={errors.monthly_bill} hint="Optional — helps us recommend the right size">
              <input
                type="number"
                className={inputCls}
                value={form.monthly_bill}
                onChange={e => set('monthly_bill', e.target.value)}
                placeholder="3000"
                min="0"
                disabled={loading}
              />
            </Field>

            <label className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-slate-300 text-amber-500 focus:ring-amber-500"
                checked={form.subsidy_interest}
                onChange={e => set('subsidy_interest', e.target.checked)}
                disabled={loading}
              />
              <span className="text-sm text-slate-700">
                I'm interested in government subsidy (PM Surya Ghar)
              </span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="mt-2 flex items-center justify-center gap-2 rounded-xl bg-amber-500 py-3 font-bold text-white hover:bg-amber-600 disabled:opacity-60 transition-colors"
            >
              {loading && <Spinner size="sm" />}
              {loading ? 'Submitting…' : 'Submit Enquiry'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
