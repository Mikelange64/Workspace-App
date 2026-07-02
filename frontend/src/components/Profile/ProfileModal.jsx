import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../../context/AuthContext'
import {
  updateUser,
  changePassword,
  deleteAccount,
  removeAvatar,
  uploadAvatarRequest,
} from '../../api/client'
import './ProfileModal.css'

function toAvatarUrl(path) {
  return path?.startsWith('https://') ? path : null
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  )
}

function AccountPanel({ user, refreshUser, logout, onClose, onToast }) {
  const avatarUrl = toAvatarUrl(user.image_path)
  const initials = user.username?.[0]?.toUpperCase() ?? '?'
  const fileRef = useRef(null)

  const [username, setUsername] = useState(user.username ?? '')
  const [email, setEmail] = useState(user.email ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [avatarLoading, setAvatarLoading] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const isDirty = username.trim() !== (user.username ?? '') || email.trim() !== (user.email ?? '')

  async function handleSave() {
    if (!isDirty) return
    setSaving(true)
    setSaveError('')
    const patch = {}
    if (username.trim() !== user.username) patch.username = username.trim()
    if (email.trim() !== user.email) patch.email = email.trim()
    try {
      await updateUser(patch)
      await refreshUser()
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setSaveError(err.detail ?? 'Could not save changes')
    } finally {
      setSaving(false)
    }
  }

  async function handleAvatarChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarLoading(true)
    try {
      await uploadAvatarRequest(file)
      await refreshUser()
    } catch (err) {
      onToast?.(err.detail ?? 'Could not upload picture')
    } finally {
      setAvatarLoading(false)
      e.target.value = ''
    }
  }

  async function handleRemoveAvatar() {
    setAvatarLoading(true)
    try {
      await removeAvatar()
      await refreshUser()
    } catch (err) {
      onToast?.(err.detail ?? 'Could not remove picture')
    } finally {
      setAvatarLoading(false)
    }
  }

  async function handleDeleteAccount() {
    if (!confirmDelete) {
      setConfirmDelete(true)
      return
    }
    setDeleting(true)
    try {
      await deleteAccount()
      logout()
      onClose()
    } catch (err) {
      onToast?.(err.detail ?? 'Could not delete account')
      setDeleting(false)
      setConfirmDelete(false)
    }
  }

  return (
    <div className="pm-panel">
      <h2 className="pm-panel__title">Account</h2>

      <div className="pm-avatar-section">
        <div className="pm-avatar">
          {avatarUrl
            ? <img src={avatarUrl} alt="" className="pm-avatar__img" />
            : <span className="pm-avatar__initials">{initials}</span>
          }
        </div>
        <div className="pm-avatar-actions">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="pm-avatar-file"
            onChange={handleAvatarChange}
            tabIndex={-1}
          />
          <button
            type="button"
            className="pm-btn pm-btn--secondary"
            onClick={() => fileRef.current?.click()}
            disabled={avatarLoading}
          >
            {avatarLoading ? 'Uploading…' : 'Upload picture'}
          </button>
          {avatarUrl && (
            <button
              type="button"
              className="pm-btn pm-btn--ghost"
              onClick={handleRemoveAvatar}
              disabled={avatarLoading}
            >
              Remove
            </button>
          )}
        </div>
      </div>

      <div className="pm-fields">
        <div className="pm-field">
          <label className="pm-field__label" htmlFor="pm-username">Username</label>
          <input
            id="pm-username"
            type="text"
            className="pm-field__input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSave() }}
            autoComplete="username"
          />
        </div>

        <div className="pm-field">
          <label className="pm-field__label" htmlFor="pm-email">Email</label>
          <input
            id="pm-email"
            type="email"
            className="pm-field__input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSave() }}
            autoComplete="email"
          />
        </div>

        {saveError && <p className="pm-field__error">{saveError}</p>}

        <button
          type="button"
          className="pm-btn pm-btn--primary"
          onClick={handleSave}
          disabled={!isDirty || saving}
        >
          {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save changes'}
        </button>
      </div>

      <div className="pm-danger-zone">
        <h3 className="pm-danger-zone__title">Delete account</h3>
        <p className="pm-danger-zone__desc">
          Permanently removes your account and all associated data. This cannot be undone.
        </p>
        {confirmDelete && (
          <p className="pm-danger-zone__confirm-msg">Are you sure? This will delete everything.</p>
        )}
        <div className="pm-danger-zone__actions">
          <button
            type="button"
            className="pm-btn pm-btn--danger"
            onClick={handleDeleteAccount}
            disabled={deleting}
          >
            {deleting ? 'Deleting…' : confirmDelete ? 'Yes, delete my account' : 'Delete my account'}
          </button>
          {confirmDelete && (
            <button
              type="button"
              className="pm-btn pm-btn--ghost"
              onClick={() => setConfirmDelete(false)}
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function SecurityPanel() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (next !== confirm) { setError('New passwords do not match'); return }
    if (next.length < 8) { setError('Password must be at least 8 characters'); return }
    setSaving(true)
    try {
      await changePassword(current, next)
      setSaved(true)
      setCurrent('')
      setNext('')
      setConfirm('')
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err.detail ?? 'Could not update password')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="pm-panel">
      <h2 className="pm-panel__title">Security</h2>
      <form className="pm-form" onSubmit={handleSubmit} noValidate>
        <div className="pm-field">
          <label className="pm-field__label" htmlFor="pm-current-pw">Current password</label>
          <input
            id="pm-current-pw"
            type="password"
            className="pm-field__input"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        <div className="pm-field">
          <label className="pm-field__label" htmlFor="pm-new-pw">New password</label>
          <input
            id="pm-new-pw"
            type="password"
            className="pm-field__input"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        <div className="pm-field">
          <label className="pm-field__label" htmlFor="pm-confirm-pw">Confirm new password</label>
          <input
            id="pm-confirm-pw"
            type="password"
            className={`pm-field__input${confirm && confirm !== next ? ' pm-field__input--error' : ''}`}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
          />
        </div>
        {error && <p className="pm-form__error" role="alert">{error}</p>}
        {saved && <p className="pm-form__success">Password updated successfully.</p>}
        <button
          type="submit"
          className="pm-btn pm-btn--primary"
          disabled={saving || !current || !next || !confirm}
        >
          {saving ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </div>
  )
}

const TABS = [
  { id: 'account', label: 'Account' },
  { id: 'security', label: 'Security' },
]

function ProfileModal({ onClose, onToast }) {
  const { user, refreshUser, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('account')

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="pm-backdrop" onClick={onClose}>
      <div
        className="pm-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Account settings"
        onClick={(e) => e.stopPropagation()}
      >
        <nav className="pm-nav" aria-label="Settings sections">
          <p className="pm-nav__header">Settings</p>
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={`pm-nav__item${activeTab === tab.id ? ' pm-nav__item--active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="pm-body">
          <button type="button" className="pm-close" onClick={onClose} aria-label="Close settings">
            <CloseIcon />
          </button>
          {activeTab === 'account' && (
            <AccountPanel user={user} refreshUser={refreshUser} logout={logout} onClose={onClose} onToast={onToast} />
          )}
          {activeTab === 'security' && <SecurityPanel />}
        </div>
      </div>
    </div>
  )
}

export default ProfileModal
