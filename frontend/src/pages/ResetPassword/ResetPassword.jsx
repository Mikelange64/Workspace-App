import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import { resetPassword } from '../../api/client'
import '../auth.css'

function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await resetPassword(token, password)
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.detail ?? 'Something went wrong. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1 className="auth-card__heading">Invalid link</h1>
          <p className="auth-card__subtext">This password reset link is missing or malformed.</p>
          <p className="auth-card__footer">
            <Link to="/forgot-password">Request a new link</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-card__heading">Set new password</h1>
        <p className="auth-card__subtext">Choose a new password for your account.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="reset-password">New password</label>
            <input
              id="reset-password"
              type="password"
              className="auth-form__input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              autoFocus
              required
            />
          </div>
          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="reset-confirm">Confirm password</label>
            <input
              id="reset-confirm"
              type="password"
              className={`auth-form__input${confirm && confirm !== password ? ' auth-form__input--error' : ''}`}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>

          {error && <p className="auth-form__error-banner" role="alert">{error}</p>}

          <button
            type="submit"
            className="auth-form__submit"
            disabled={loading || !password || !confirm}
          >
            {loading ? 'Saving…' : 'Set new password'}
          </button>
        </form>

        <p className="auth-card__footer">
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  )
}

export default ResetPassword
