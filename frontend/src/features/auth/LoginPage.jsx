import React, { useState } from 'react'
import { useNavigate, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../app/AuthContext.jsx'
import Field, { inputCls } from '../../app/components/Field.jsx'
import Spinner from '../../app/components/Spinner.jsx'

export default function LoginPage() {
  const { login, currentUser } = useAuth()
  const navigate  = useNavigate()
  const location  = useLocation()
  const from      = location.state?.from?.pathname || '/dashboard'

  const [form, setForm]       = useState({ email: '', password: '' })
  const [errors, setErrors]   = useState({})
  const [loading, setLoading] = useState(false)
  const [serverErr, setServerErr] = useState('')

  if (currentUser) return <Navigate to={from} replace />

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const validate = () => {
    const e = {}
    if (!form.email)    e.email    = 'Email is required'
    if (!form.password) e.password = 'Password is required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    setServerErr('')
    try {
      await login(form.email, form.password)
      navigate(from, { replace: true })
    } catch (err) {
      setServerErr(err.message || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl p-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-2">☀️</div>
          <h1 className="text-2xl font-bold text-slate-900">SunPower</h1>
          <p className="text-sm text-slate-500 mt-1">Staff portal — sign in to continue</p>
        </div>

        {serverErr && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {serverErr}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <Field label="Email" error={errors.email} required>
            <input
              type="email"
              className={inputCls}
              value={form.email}
              onChange={e => set('email', e.target.value)}
              placeholder="director@sunpower.test"
              autoFocus
              disabled={loading}
            />
          </Field>

          <Field label="Password" error={errors.password} required>
            <input
              type="password"
              className={inputCls}
              value={form.password}
              onChange={e => set('password', e.target.value)}
              placeholder="••••••••"
              disabled={loading}
            />
          </Field>

          <button
            type="submit"
            disabled={loading}
            className="mt-2 flex items-center justify-center gap-2 rounded-lg bg-amber-500 px-4 py-2.5 font-semibold text-white hover:bg-amber-600 disabled:opacity-60 transition-colors"
          >
            {loading && <Spinner size="sm" />}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-400">
          <a href="/" className="hover:text-amber-500 transition-colors">← Back to website</a>
        </p>
      </div>
    </div>
  )
}
