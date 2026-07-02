import { useState, useEffect, useRef } from 'react'
import './NewWorkspaceModal.css'

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

function getDaysInMonth(year, month) {
  return new Date(year, month, 0).getDate()
}

function getCalendarDays(year, month) {
  const firstDay = new Date(year, month - 1, 1)
  const start = new Date(firstDay)
  start.setDate(1 - firstDay.getDay())
  const days = []
  const cur = new Date(start)
  while (days.length < 42) {
    days.push(new Date(cur))
    cur.setDate(cur.getDate() + 1)
  }
  return days
}

function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
}

// ─── Spinner field (matches CalendarModal style) ─────────────────────────────

function SpinnerField({ value, min, max, onChange, width, wrap, disabled }) {
  const [draft, setDraft] = useState(String(value))
  useEffect(() => { setDraft(String(value)) }, [value])

  function inc() {
    if (disabled) return
    onChange(wrap ? (value >= max ? min : value + 1) : Math.min(max, value + 1))
  }
  function dec() {
    if (disabled) return
    onChange(wrap ? (value <= min ? max : value - 1) : Math.max(min, value - 1))
  }
  function commit() {
    const parsed = parseInt(draft, 10)
    if (!isNaN(parsed) && parsed >= min && parsed <= max) onChange(parsed)
    else setDraft(String(value))
  }

  return (
    <div className={`nwm-spinner${disabled ? ' nwm-spinner--disabled' : ''}`} style={{ width }}>
      <button type="button" className="nwm-spinner__btn" onClick={inc} tabIndex={-1} aria-label="Increase" disabled={disabled}>
        <TriangleUp />
      </button>
      <input
        className="nwm-spinner__val"
        inputMode="numeric"
        value={draft}
        disabled={disabled}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onFocus={() => !disabled && setDraft(String(value))}
        onKeyDown={(e) => { if (e.key === 'Enter') commit() }}
      />
      <button type="button" className="nwm-spinner__btn" onClick={dec} tabIndex={-1} aria-label="Decrease" disabled={disabled}>
        <TriangleDown />
      </button>
    </div>
  )
}

// ─── Mini calendar popover ───────────────────────────────────────────────────

function MiniCalPopover({ selectedDate, onSelect, onClose }) {
  const today = new Date()
  const [year, setYear] = useState(selectedDate ? selectedDate.getFullYear() : today.getFullYear())
  const [month, setMonth] = useState(selectedDate ? selectedDate.getMonth() + 1 : today.getMonth() + 1)
  const ref = useRef(null)

  useEffect(() => {
    function onDown(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [onClose])

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }
  function nextMonth() {
    if (month === 12) { setMonth(1); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }

  const days = getCalendarDays(year, month)

  return (
    <div className="nwm-cal-pop" ref={ref} role="dialog" aria-label="Pick a date">
      <div className="nwm-cal-pop__header">
        <button type="button" className="nwm-cal-pop__nav" onClick={prevMonth} aria-label="Previous month">
          <ChevronLeft />
        </button>
        <span className="nwm-cal-pop__title">{MONTH_NAMES[month - 1]} {year}</span>
        <button type="button" className="nwm-cal-pop__nav" onClick={nextMonth} aria-label="Next month">
          <ChevronRight />
        </button>
      </div>

      <div className="nwm-cal-pop__grid">
        {['S','M','T','W','T','F','S'].map((d, i) => (
          <span key={i} className="nwm-cal-pop__dow">{d}</span>
        ))}
        {days.map((date, i) => {
          const inMonth = date.getMonth() + 1 === month
          const isToday = isSameDay(date, today)
          const isSel = selectedDate && isSameDay(date, selectedDate)
          return (
            <button
              key={i}
              type="button"
              className={[
                'nwm-cal-pop__day',
                !inMonth ? 'nwm-cal-pop__day--other' : '',
                isToday ? 'nwm-cal-pop__day--today' : '',
                isSel ? 'nwm-cal-pop__day--selected' : '',
              ].filter(Boolean).join(' ')}
              onClick={() => { if (inMonth) { onSelect(date); onClose() } }}
              disabled={!inMonth}
              tabIndex={inMonth ? 0 : -1}
            >
              {date.getDate()}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ─── Main modal ──────────────────────────────────────────────────────────────

function NewWorkspaceModal({ onClose, onCreate, defaultDueDate = null }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [maxMembers, setMaxMembers] = useState('')
  const [showCalPop, setShowCalPop] = useState(false)

  const today = new Date()
  const [hasDate, setHasDate] = useState(!!defaultDueDate)
  const [day, setDay] = useState(defaultDueDate ? defaultDueDate.getDate() : today.getDate())
  const [month, setMonth] = useState(defaultDueDate ? defaultDueDate.getMonth() + 1 : today.getMonth() + 1)
  const [year, setYear] = useState(defaultDueDate ? defaultDueDate.getFullYear() : today.getFullYear())

  function clampDay(d, m, y) {
    return Math.min(d, getDaysInMonth(y, m))
  }

  function handleDayChange(v) { setDay(v); setHasDate(true) }
  function handleMonthChange(v) {
    setMonth(v)
    setDay(d => clampDay(d, v, year))
    setHasDate(true)
  }
  function handleYearChange(v) {
    setYear(v)
    setDay(d => clampDay(d, month, v))
    setHasDate(true)
  }

  function handleCalendarPick(date) {
    setDay(date.getDate())
    setMonth(date.getMonth() + 1)
    setYear(date.getFullYear())
    setHasDate(true)
  }

  function clearDate() {
    setHasDate(false)
  }

  const selectedDate = hasDate ? new Date(year, month - 1, day) : null

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await onCreate({
        title: title.trim(),
        description: description.trim() || null,
        due_date: selectedDate ? selectedDate.toISOString() : null,
        max_number: maxMembers ? parseInt(maxMembers, 10) : null,
      })
    } catch (err) {
      setError(err.detail ?? 'Failed to create workspace')
      setLoading(false)
    }
  }

  const maxMembersValid =
    maxMembers.trim() === '' || (/^\d+$/.test(maxMembers.trim()) && parseInt(maxMembers, 10) >= 1)

  const canSubmit = title.trim().length > 0 && maxMembersValid && !loading

  return (
    <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div className="modal__header">
          <h2 className="modal__title" id="modal-title">New workspace</h2>
          <button type="button" className="modal__close" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        <form className="modal__body" onSubmit={handleSubmit} noValidate>
          <div className="modal__field">
            <label className="modal__label" htmlFor="ws-title">Name</label>
            <input
              id="ws-title"
              type="text"
              className="modal__input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={50}
              required
              autoFocus
            />
          </div>

          <div className="modal__field">
            <label className="modal__label" htmlFor="ws-desc">Description (optional)</label>
            <textarea
              id="ws-desc"
              className="modal__textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={3}
            />
          </div>

          <div className="modal__row">
            <div className="modal__field">
              <label className="modal__label">Due date</label>
              <div className="nwm-date-row">
                <div className="nwm-spinners">
                  <SpinnerField value={day} min={1} max={getDaysInMonth(year, month)} onChange={handleDayChange} width="44px" wrap={false} disabled={false} />
                  <span className="nwm-date-sep">/</span>
                  <SpinnerField value={month} min={1} max={12} onChange={handleMonthChange} width="38px" wrap={true} disabled={false} />
                  <span className="nwm-date-sep">/</span>
                  <SpinnerField value={year} min={2020} max={2099} onChange={handleYearChange} width="54px" wrap={false} disabled={false} />
                </div>
                <div className="nwm-date-btns">
                  <button
                    type="button"
                    className={`nwm-cal-icon${showCalPop ? ' nwm-cal-icon--active' : ''}`}
                    onClick={() => setShowCalPop(v => !v)}
                    aria-label="Open calendar"
                  >
                    <CalIcon />
                  </button>
                  {hasDate && (
                    <button type="button" className="nwm-clear-btn" onClick={clearDate} aria-label="Clear date">
                      ✕
                    </button>
                  )}
                </div>
              </div>
              <span className="nwm-no-deadline" style={{ visibility: hasDate ? 'hidden' : 'visible' }}>No deadline</span>
              {showCalPop && (
                <MiniCalPopover
                  selectedDate={selectedDate}
                  onSelect={handleCalendarPick}
                  onClose={() => setShowCalPop(false)}
                />
              )}
            </div>

            <div className="modal__field">
              <label className="modal__label" htmlFor="ws-max">Max members</label>
              <input
                id="ws-max"
                type="text"
                inputMode="numeric"
                className="modal__input"
                placeholder="No limit"
                value={maxMembers}
                onChange={(e) => setMaxMembers(e.target.value)}
              />
            </div>
          </div>

          {error && <p className="modal__error" role="alert">{error}</p>}

          <div className="modal__footer">
            <button type="button" className="modal__btn modal__btn--secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="modal__btn modal__btn--primary" disabled={!canSubmit}>
              {loading ? 'Creating…' : 'Create workspace'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function CalIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function ChevronLeft() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

function ChevronRight() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function TriangleUp() {
  return (
    <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true">
      <path d="M5 0 L10 6 L0 6 Z" fill="currentColor" />
    </svg>
  )
}

function TriangleDown() {
  return (
    <svg viewBox="0 0 10 6" width="10" height="6" aria-hidden="true">
      <path d="M5 6 L10 0 L0 0 Z" fill="currentColor" />
    </svg>
  )
}

export default NewWorkspaceModal
