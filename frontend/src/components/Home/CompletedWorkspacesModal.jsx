import { useState, useEffect, useRef } from 'react'
import { getCompletedWorkspaces } from '../../api/client'
import { formatAbsoluteDate } from '../../utils/date'
import './CompletedWorkspacesModal.css'

const LIMIT = 20

function normalizeWs(ws) {
  return {
    id: ws.id,
    title: ws.title,
    dueDate: ws.due_date ?? null,
    completedAt: ws.completed_at ?? null,
    numOfTasks: ws.num_of_tasks ?? 0,
  }
}

function CompletedWorkspacesModal({ onClose, onSelectWorkspace }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const sentinelRef = useRef(null)

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    let cancelled = false
    const state = { loading: false, hasMore: true, skip: 0 }
    setItems([])
    setLoading(true)

    async function load() {
      if (cancelled || state.loading || !state.hasMore) return
      state.loading = true
      try {
        const data = await getCompletedWorkspaces(state.skip, LIMIT)
        if (cancelled) return
        setItems((prev) => [...prev, ...data.workspaces.map(normalizeWs)])
        state.skip += data.workspaces.length
        state.hasMore = data.has_more
      } catch { /* silent */ }
      finally {
        state.loading = false
        if (!cancelled) setLoading(false)
      }
    }

    load()

    const obs = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) load() },
      { threshold: 0.1 }
    )
    if (sentinelRef.current) obs.observe(sentinelRef.current)
    return () => { cancelled = true; obs.disconnect() }
  }, [])

  return (
    <div
      className="cw-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="cw-modal" role="dialog" aria-label="Completed workspaces">
        <div className="cw-modal__header">
          <h2 className="cw-modal__title">Completed workspaces</h2>
          <button type="button" className="cw-modal__close" onClick={onClose} aria-label="Close">
            <CloseIcon />
          </button>
        </div>

        <div className="cw-modal__list">
          {items.map((ws) => (
            <button
              key={ws.id}
              type="button"
              className="cw-item"
              onClick={() => { onSelectWorkspace(ws.id); onClose() }}
            >
              <div className="cw-item__main">
                <span className="cw-item__check" aria-hidden="true" />
                <span className="cw-item__title">{ws.title}</span>
              </div>
              <div className="cw-item__meta">
                <span>{ws.numOfTasks} task{ws.numOfTasks !== 1 ? 's' : ''}</span>
                {ws.completedAt
                  ? <span>Completed {formatAbsoluteDate(ws.completedAt)}</span>
                  : <span>—</span>
                }
              </div>
            </button>
          ))}

          {loading && (
            <p className="cw-modal__loading">Loading…</p>
          )}

          {!loading && items.length === 0 && (
            <p className="cw-modal__empty">No completed workspaces yet.</p>
          )}

          <div ref={sentinelRef} className="cw-modal__sentinel" />
        </div>
      </div>
    </div>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export default CompletedWorkspacesModal
