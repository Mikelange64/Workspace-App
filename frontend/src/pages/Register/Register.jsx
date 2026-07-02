import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import '../auth.css'
import './Register.css'

function EyeIcon({ open }) {
  return open ? (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  ) : (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  )
}

function CameraIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  )
}

function Register() {
  const { register } = useAuth()
  const fileInputRef = useRef(null)

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [avatarFile, setAvatarFile] = useState(null)
  const [avatarPreview, setAvatarPreview] = useState(null)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    return () => {
      if (avatarPreview) URL.revokeObjectURL(avatarPreview)
    }
  }, [avatarPreview])

  function handleAvatarChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarFile(file)
    setAvatarPreview(URL.createObjectURL(file))
  }

  function validate() {
    const errs = {}
    if (username.trim().length < 5) errs.username = 'Must be at least 5 characters'
    if (!email.includes('@')) errs.email = 'Enter a valid email address'
    if (password.length < 8) errs.password = 'Must be at least 8 characters'
    if (password !== confirm) errs.confirm = 'Passwords do not match'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const errs = validate()
    setFieldErrors(errs)
    if (Object.keys(errs).length > 0) return

    setLoading(true)
    try {
      await register(username.trim(), email.trim(), password)
      setSuccess(true)
    } catch (err) {
      setError(err.detail ?? 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-page__panel">
            <h1 className="auth-card__heading">Check your email</h1>
          <p className="auth-card__subtext">
            We sent a verification link to <strong>{email}</strong>.
            Click it to activate your account, then sign in.
          </p>
          <p className="auth-card__footer">
            <Link to="/login">Go to sign in</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-page__panel">
        <h1 className="auth-card__heading">Create your account</h1>
        <p className="auth-card__subtext">Get started with Filobelo</p>

        <form className="auth-form" onSubmit={handleSubmit} noValidate>
          {/* Avatar picker */}
          <div className="auth-form__group auth-form__group--avatar">
            <input
              ref={fileInputRef}
              id="reg-avatar"
              type="file"
              accept="image/*"
              className="reg-avatar__input"
              onChange={handleAvatarChange}
            />
            <button
              type="button"
              className="reg-avatar__trigger"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Choose profile picture"
            >
              {avatarPreview ? (
                <img src={avatarPreview} alt="Preview" className="reg-avatar__preview" />
              ) : (
                <span className="reg-avatar__placeholder">
                  <CameraIcon />
                </span>
              )}
              <span className="reg-avatar__label">
                {avatarPreview ? 'Change photo' : 'Add photo'}
              </span>
            </button>
          </div>

          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="reg-username">
              Username
            </label>
            <input
              id="reg-username"
              type="text"
              className={`auth-form__input${fieldErrors.username ? ' auth-form__input--error' : ''}`}
              value={username}
              onChange={(e) => { setUsername(e.target.value); setFieldErrors((p) => ({ ...p, username: '' })) }}
              autoComplete="username"
              autoFocus
              required
            />
            {fieldErrors.username && (
              <span className="auth-form__field-error">{fieldErrors.username}</span>
            )}
          </div>

          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="reg-email">
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              className={`auth-form__input${fieldErrors.email ? ' auth-form__input--error' : ''}`}
              value={email}
              onChange={(e) => { setEmail(e.target.value); setFieldErrors((p) => ({ ...p, email: '' })) }}
              autoComplete="email"
              required
            />
            {fieldErrors.email && (
              <span className="auth-form__field-error">{fieldErrors.email}</span>
            )}
          </div>

          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="reg-password">
              Password
            </label>
            <div className="auth-form__input-wrap">
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                className={`auth-form__input auth-form__input--password${fieldErrors.password ? ' auth-form__input--error' : ''}`}
                value={password}
                onChange={(e) => { setPassword(e.target.value); setFieldErrors((p) => ({ ...p, password: '' })) }}
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                className="auth-form__show-toggle"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                <EyeIcon open={showPassword} />
              </button>
            </div>
            {fieldErrors.password && (
              <span className="auth-form__field-error">{fieldErrors.password}</span>
            )}
          </div>

          <div className="auth-form__group">
            <label className="auth-form__label" htmlFor="reg-confirm">
              Confirm password
            </label>
            <input
              id="reg-confirm"
              type="password"
              className={`auth-form__input${confirm && confirm !== password ? ' auth-form__input--error' : ''}${fieldErrors.confirm ? ' auth-form__input--error' : ''}`}
              value={confirm}
              onChange={(e) => { setConfirm(e.target.value); setFieldErrors((p) => ({ ...p, confirm: '' })) }}
              autoComplete="new-password"
              required
            />
            {fieldErrors.confirm && (
              <span className="auth-form__field-error">{fieldErrors.confirm}</span>
            )}
          </div>

          {error && (
            <p className="auth-form__error-banner" role="alert">{error}</p>
          )}

          <button
            type="submit"
            className="auth-form__submit"
            disabled={loading || (confirm && confirm !== password)}
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth-card__footer">
          Already have an account?{' '}
          <Link to="/login">Sign in</Link>
        </p>
      {/* </div> */}
      </div>
    </div>
  )
}

export default Register
