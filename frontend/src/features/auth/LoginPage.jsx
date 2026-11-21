import React, { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../app/AuthContext'
import { homeFor } from '../../app/navigation'
import Field from '../../app/components/Field'
import PublicFrame from '../public/PublicFrame'

export default function LoginPage() {
  const { login, currentUser } = useAuth()
  const { state } = useLocation()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (currentUser)
    return (
      <Navigate
        to={state?.from ? state.from.pathname + state.from.search : homeFor(currentUser.role)}
        replace
      />
    )
  async function submit(event) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setBusy(true)
    setError('')
    try {
      await login(form.get('email').trim(), form.get('password'))
    } catch (err) {
      setError(err.message || 'Could not sign in.')
    } finally {
      setBusy(false)
    }
  }
  return (
    <PublicFrame>
      <div className="login-grid">
        <div className="login-photo">
          <img src="/solar-array.jpg" alt="" />
        </div>
        <section className="login-form">
          <h1>Staff sign in</h1>
          <p>Sign in to your SunPower workspace.</p>
          <form onSubmit={submit} className="stack">
            <Field label="Work email">
              <input type="email" name="email" autoComplete="username" required />
            </Field>
            <Field label="Password">
              <input type="password" name="password" autoComplete="current-password" required />
            </Field>
            {error && (
              <p role="alert" className="form-error">
                {error}
              </p>
            )}
            <button className="button primary" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in →'}
            </button>
          </form>
        </section>
      </div>
    </PublicFrame>
  )
}
