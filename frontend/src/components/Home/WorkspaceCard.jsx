import { useState, useEffect, useRef } from 'react'
import { getWorkspaceUrgency } from '../../utils/workspaceStatus'
import { formatDueDate } from '../../utils/date'
import './WorkspaceCard.css'

const URGENCY_VAR = {
  error:   'var(--color-error)',
  warning: 'var(--color-warning)',
  success: 'var(--color-success)',
  neutral: 'var(--color-neutral)',
}

function getCardAccent(workspace) {
  return URGENCY_VAR[getWorkspaceUrgency(workspace)]
}

function ContextMenu({ x, y, onComplete, onClose }) {
  const ref = useRef(null)

  useEffect(() => {
    function handleDown(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handleDown)
    return () => document.removeEventListener('mousedown', handleDown)
  }, [onClose])

  return (
    <div
      ref={ref}
      className="ws-ctx-menu"
      style={{ top: y, left: x }}
      onContextMenu={(e) => e.preventDefault()}
    >
      <button
        type="button"
        className="ws-ctx-menu__item ws-ctx-menu__item--complete"
        onClick={() => { onComplete(); onClose() }}
      >
        Mark complete
      </button>
    </div>
  )
}

function WorkspaceCard({ workspace, members, onSelect, onComplete }) {
  const accent = getCardAccent(workspace)
  const [ctxMenu, setCtxMenu] = useState(null)

  // Use real member objects when available; otherwise generate placeholders from the count
  // so circles always render even before member data is wired up from the API.
  const totalCount = members?.length ?? (workspace.numOfMembers ?? 0)
  const memberList = members ?? Array.from(
    { length: Math.min(totalCount, 3) },
    (_, i) => ({ id: `ph-${i}`, name: null, avatarUrl: null })
  )
  const visibleMembers = memberList.slice(0, 3)
  const overflowCount = Math.max(totalCount - 3, 0)

  function handleContextMenu(e) {
    if (!onComplete) return
    e.preventDefault()
    setCtxMenu({ x: e.clientX, y: e.clientY })
  }

  return (
    <>
      <button
        type="button"
        className="workspace-card"
        onClick={() => onSelect?.(workspace.id)}
        onContextMenu={handleContextMenu}
      >
        <div className="workspace-card__highlight" style={{ backgroundColor: accent }} />

        <div className="workspace-card__body">
          <h3 className="workspace-card__title">{workspace.title}</h3>

          <div className="workspace-card__meta">
            <span className="workspace-card__status" style={{ color: accent }}>
              {formatDueDate(workspace.dueDate)}
            </span>
            <span className="workspace-card__pct">
              {Math.round(workspace.progress ?? 0)}<span className="workspace-card__pct-symbol">%</span>
            </span>
          </div>

          <div className="workspace-card__progress-track">
            <div
              className="workspace-card__progress-fill"
              style={{ width: `${workspace.progress ?? 0}%`, backgroundColor: accent }}
            />
          </div>

          <div className="workspace-card__footer">
            <span className="workspace-card__task-count">
              {workspace.numOfTasks ?? 0} task{workspace.numOfTasks === 1 ? '' : 's'}
            </span>

            <span className="workspace-card__avatars">
              {visibleMembers.map((member) => (
                <span key={member.id} className="workspace-card__avatar">
                  {member.avatarUrl ? (
                    <img src={member.avatarUrl} alt={member.name ?? ''} />
                  ) : member.name ? (
                    member.name[0].toUpperCase()
                  ) : null}
                </span>
              ))}
              {overflowCount > 0 && (
                <span className="workspace-card__avatar workspace-card__avatar--overflow">
                  +{overflowCount}
                </span>
              )}
            </span>
          </div>
        </div>
      </button>

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          onComplete={() => onComplete?.(workspace.id)}
          onClose={() => setCtxMenu(null)}
        />
      )}
    </>
  )
}

export default WorkspaceCard
