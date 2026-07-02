import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { verifyEmail } from '../../api/client'
import filobeloProud from '../../assets/mascott/filobelo_proud.svg'
import '../auth.css'

function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [status, setStatus] = useState('loading') // 'loading' | 'success' | 'error'
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setError('This verification link is missing or malformed.')
      return
    }

    verifyEmail(token)
      .then(() => setStatus('success'))
      .catch((err) => {
        setStatus('error')
        setError(err.detail ?? 'This verification link is invalid or has expired.')
      })
  }, [token])

  if (status === 'loading') {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <p className="auth-card__subtext">Verifying your email…</p>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-card__mascot">
            <img src={filobeloProud} alt="" className="auth-card__mascot-img" />
          </div>
          <h1 className="auth-card__heading">Email verified</h1>
          <p className="auth-card__subtext">Your account is now active. You can sign in.</p>
          <p className="auth-card__footer">
            <Link to="/login">Go to sign in</Link>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-card__heading">Verification failed</h1>
        <p className="auth-card__subtext">{error}</p>
        <p className="auth-card__footer">
          <Link to="/register">Create a new account</Link>
        </p>
      </div>
    </div>
  )
}

export default VerifyEmail
