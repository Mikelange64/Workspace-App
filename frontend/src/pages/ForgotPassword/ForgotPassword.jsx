import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../../api/client'
import '../auth.css'

function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await forgotPassword(email.trim())
      setSent(true)
    } catch (err) {
      setError(err.detail ?? 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-page__panel">
          <h1 className="auth-card__heading">Check your email</h1>
          <p className="auth-card__subtext">
            If an account exists for <strong>{email}</strong>, you&apos;ll receive a reset link shortly.
          </p>
          <p className="auth-card__footer">
            <Link to="/login">Back to sign in</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-page__panel">
        <h1 className="auth-card__heading">Reset your password</h1>
        <p className="auth-card__subtext">Enter your email and we&apos;ll send you a reset link.</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="forgot-email">Email</label>
            <input
              id="forgot-email"
              type="email"
              className="auth-form__input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              autoFocus
              required
            />
          </div>

          {error && <p className="auth-form__error-banner" role="alert">{error}</p>}

          <button
            type="submit"
            className="auth-form__submit"
            disabled={loading || !email.trim()}
          >
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
        </form>

        <p className="auth-card__footer">
          <Link to="/login">Back to sign in</Link>
        </p>
      </div>
    </div>
  )
}

export default ForgotPassword
