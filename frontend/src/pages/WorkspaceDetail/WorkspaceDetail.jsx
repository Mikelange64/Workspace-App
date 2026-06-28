import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link, useNavigate, useOutletContext } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import {
  authFetch,
  getWorkspace,
  createTask,
  patchTask,
  deleteTask,
  toggleTask,
  patchWorkspace,
  getMembersWithRoles,
  inviteMember,
  promoteToAdmin,
  removeMember,
  searchUser,
  reassignTask,
} from '../../api/client'
import { getDaysRemaining, formatDueDate } from '../../utils/date'
import { getWorkspaceUrgency } from '../../utils/workspaceStatus'
import useDismissableMenu from '../../hooks/useDismissableMenu'
import './WorkspaceDetail.css'

// ─── helpers ────────────────────────────────────────────────────────────────

function toAvatarUrl(path) {
  return path?.startsWith('https://') ? path : null
}

function getTaskUrgency(dueDate) {
  if (!dueDate) return 'neutral'
  const d = getDaysRemaining(dueDate)
  if (d < 0) return 'error'
  if (d <= 3) return 'warning'
  return 'success'
}

function normalizeTask(t) {
  return {
    id: t.id,
    title: t.title,
    dueDate: t.due_date ?? null,
    isCompleted: t.is_completed,
    ownerId: t.owner_id,
  }
}

function normalizeWorkspace(ws) {
  return {
    id: ws.id,
    creatorId: ws.creator_id,
    title: ws.title,
    description: ws.description,
    dueDate: ws.due_date ?? null,
    currentUserRole: ws.current_user_role ?? null,
    members: (ws.members ?? []).map((m) => ({
      id: m.id,
      name: m.username,
      avatarUrl: toAvatarUrl(m.image_path),
    })),
  }
}

function sortByUrgency(tasks) {
  return [...tasks].sort((a, b) => {
    const dA = getDaysRemaining(a.dueDate)
    const dB = getDaysRemaining(b.dueDate)
    if (dA === null && dB === null) return 0
    if (dA === null) return 1
    if (dB === null) return -1
    return dA - dB
  })
}

// ─── icons ──────────────────────────────────────────────────────────────────

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}

function DotsIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
      <circle cx="5" cy="12" r="1.6" fill="currentColor" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" />
      <circle cx="19" cy="12" r="1.6" fill="currentColor" />
    </svg>
  )
}

function CalIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true">
      <path d="M12 2L13.9 9.1L21 11L13.9 12.9L12 20L10.1 12.9L3 11L10.1 9.1Z" />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

// ─── sub-components ─────────────────────────────────────────────────────────

function MemberAvatar({ member, size = 28 }) {
  return (
    <span
      className="member-avatar"
      style={{ width: size, height: size, fontSize: Math.round(size * 0.38) }}
      title={member.name}
    >
      {member.avatarUrl
        ? <img src={member.avatarUrl} alt={member.name} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '50%' }} />
        : member.name?.[0]?.toUpperCase()
      }
    </span>
  )
}

function TaskRowMenu({ isCompleted, isOwner, isAdmin, onEdit, onToggle, onReassign, onDelete }) {
  const [isOpen, setIsOpen, ref] = useDismissableMenu()
  const canReassign = isOwner || isAdmin
  return (
    <div className="task-row__menu-wrap" ref={ref}>
      <button
        type="button"
        className="task-row__menu-trigger"
        onClick={(e) => { e.stopPropagation(); setIsOpen((v) => !v) }}
        aria-label="Task actions"
      >
        <DotsIcon />
      </button>
      {isOpen && (
        <ul className="wd-menu-list" role="menu">
          <li role="none">
            <button type="button" role="menuitem" className="wd-menu-item"
              onClick={() => { onEdit(); setIsOpen(false) }}>
              Edit
            </button>
          </li>
          {isOwner && (
            <li role="none">
              <button type="button" role="menuitem" className="wd-menu-item"
                onClick={() => { onToggle(); setIsOpen(false) }}>
                {isCompleted ? 'Mark incomplete' : 'Mark complete'}
              </button>
            </li>
          )}
          {canReassign && (
            <li role="none">
              <button type="button" role="menuitem" className="wd-menu-item"
                onClick={() => { onReassign(); setIsOpen(false) }}>
                Reassign
              </button>
            </li>
          )}
          {isAdmin && (
            <li role="none">
              <button type="button" role="menuitem" className="wd-menu-item wd-menu-item--danger"
                onClick={() => { onDelete(); setIsOpen(false) }}>
                Delete
              </button>
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

function TaskRow({ task, member, isAdmin, currentUserId, onSelect, onToggle, onReassign, onDelete }) {
  const urgency = getTaskUrgency(task.dueDate)
  const isOwner = task.ownerId === currentUserId
  return (
    <div className={`task-row${task.isCompleted ? ' task-row--completed' : ''}`}>
      {isOwner ? (
        <button
          type="button"
          className={`task-row__checkbox${task.isCompleted ? ' task-row__checkbox--checked' : ''}`}
          onClick={onToggle}
          aria-label={task.isCompleted ? 'Mark incomplete' : 'Mark complete'}
        >
          {task.isCompleted && <CheckIcon />}
        </button>
      ) : (
        <span
          className={`task-row__checkbox task-row__checkbox--readonly${task.isCompleted ? ' task-row__checkbox--checked' : ''}`}
          aria-label={task.isCompleted ? 'Complete' : 'Incomplete'}
        >
          {task.isCompleted && <CheckIcon />}
        </span>
      )}

      <button type="button" className="task-row__title" onClick={onSelect}>
        {task.title}
      </button>

      {member && (
        <span className="task-row__assignee">
          <MemberAvatar member={member} size={22} />
          <span className="task-row__name">{member.name}</span>
        </span>
      )}

      {!task.isCompleted && (
        task.dueDate
          ? (
            <span className={`task-row__due task-row__due--${urgency}`}>
              <CalIcon />
              {formatDueDate(task.dueDate)}
            </span>
          ) : (
            <span className="task-row__due task-row__due--success">On track</span>
          )
      )}

      <TaskRowMenu
        isCompleted={task.isCompleted}
        isOwner={isOwner}
        isAdmin={isAdmin}
        onEdit={onSelect}
        onToggle={onToggle}
        onReassign={onReassign}
        onDelete={onDelete}
      />
    </div>
  )
}

// Member picker modal — shown when reassigning a task
function MemberPicker({ members, currentOwnerId, onSelect, onClose }) {
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      <div className="picker-backdrop" onClick={onClose} aria-hidden="true" />
      <div className="member-picker" role="dialog" aria-label="Reassign task">
        <div className="member-picker__header">
          <span className="member-picker__title">Reassign to…</span>
          <button type="button" className="member-picker__close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <ul className="member-picker__list">
          {members.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                className={`member-picker__option${m.id === currentOwnerId ? ' member-picker__option--current' : ''}`}
                onClick={() => { onSelect(m.id); onClose() }}
              >
                <MemberAvatar member={m} size={32} />
                <span className="member-picker__name">{m.name}</span>
                {m.id === currentOwnerId && <span className="member-picker__tag">current</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </>
  )
}

// Invite panel — shown at top of Members tab for admins
function InvitePanel({ workspaceId, onMemberAdded }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [found, setFound] = useState(null)
  const [error, setError] = useState('')
  const [searching, setSearching] = useState(false)
  const [adding, setAdding] = useState(false)

  async function handleSearch() {
    const q = query.trim()
    if (!q) return
    setSearching(true)
    setFound(null)
    setError('')
    try {
      const user = await searchUser(q)
      setFound(user)
    } catch (err) {
      setError(err.status === 404 ? 'No user found with that username or email.' : 'Search failed.')
    } finally {
      setSearching(false)
    }
  }

  async function handleAdd() {
    if (!found) return
    setAdding(true)
    try {
      await inviteMember(workspaceId, found.id)
      onMemberAdded()
      setQuery('')
      setFound(null)
      setOpen(false)
    } catch (err) {
      setError(err.status === 409 ? 'Already a member of this workspace.' : (err.detail ?? 'Could not add member.'))
    } finally {
      setAdding(false)
    }
  }

  if (!open) {
    return (
      <button type="button" className="invite-trigger" onClick={() => setOpen(true)}>
        + Invite member
      </button>
    )
  }

  return (
    <div className="invite-panel">
      <p className="invite-panel__label">Search by username or email</p>
      <div className="invite-panel__row">
        <input
          className="invite-panel__input"
          placeholder="username or email@example.com"
          value={query}
          onChange={(e) => { setQuery(e.target.value); setFound(null); setError('') }}
          onKeyDown={(e) => { if (e.key === 'Enter') handleSearch() }}
          autoFocus
        />
        <button type="button" className="invite-panel__search-btn" onClick={handleSearch} disabled={searching}>
          {searching ? '…' : 'Search'}
        </button>
        <button type="button" className="invite-panel__cancel" onClick={() => { setOpen(false); setQuery(''); setFound(null); setError('') }}>
          ✕
        </button>
      </div>

      {found && (
        <div className="invite-panel__result">
          <MemberAvatar member={{ name: found.username, avatarUrl: toAvatarUrl(found.image_path) }} size={32} />
          <span className="invite-panel__result-name">{found.username}</span>
          <button type="button" className="invite-panel__add-btn" onClick={handleAdd} disabled={adding}>
            {adding ? 'Adding…' : 'Add to workspace'}
          </button>
        </div>
      )}

      {error && <p className="invite-panel__error">{error}</p>}
    </div>
  )
}

function MemberListRow({ member, isAdmin, isSelf, onRemove, onPromote, onLeave }) {
  const [menuOpen, setMenuOpen, menuRef] = useDismissableMenu()

  return (
    <li className="member-list-row">
      <MemberAvatar member={member} size={38} />
      <div className="member-list-row__info">
        <span className="member-list-row__name">{member.name}</span>
        {member.role === 'admin' && <span className="member-list-row__badge">Admin</span>}
        {isSelf && <span className="member-list-row__self">you</span>}
      </div>
      <div className="member-list-row__menu-wrap" ref={menuRef}>
        <button
          type="button"
          className="member-list-row__menu-trigger"
          onClick={(e) => { e.stopPropagation(); setMenuOpen((v) => !v) }}
          aria-label="Member actions"
        >
          <DotsIcon />
        </button>
        {menuOpen && (
          <ul className="wd-menu-list" role="menu">
            {isSelf ? (
              <li role="none">
                <button type="button" role="menuitem" className="wd-menu-item wd-menu-item--danger"
                  onClick={() => { onLeave(); setMenuOpen(false) }}>
                  Leave workspace
                </button>
              </li>
            ) : (
              <>
                <li role="none">
                  <button type="button" role="menuitem" className="wd-menu-item"
                    onClick={() => setMenuOpen(false)}>
                    Message
                  </button>
                </li>
                {isAdmin && member.role !== 'admin' && (
                  <li role="none">
                    <button type="button" role="menuitem" className="wd-menu-item"
                      onClick={() => { onPromote(member.id); setMenuOpen(false) }}>
                      Promote to Admin
                    </button>
                  </li>
                )}
                {isAdmin && (
                  <li role="none">
                    <button type="button" role="menuitem" className="wd-menu-item wd-menu-item--danger"
                      onClick={() => { onRemove(member.id); setMenuOpen(false) }}>
                      Remove from workspace
                    </button>
                  </li>
                )}
              </>
            )}
          </ul>
        )}
      </div>
    </li>
  )
}

function SettingsTab({ workspace, isAdmin, isCreator, workspaceId, onWorkspaceUpdate, onDelete, onLeave }) {
  const [title, setTitle] = useState(workspace.title)
  const [description, setDescription] = useState(workspace.description)
  const [dueDate, setDueDate] = useState(
    workspace.dueDate ? workspace.dueDate.split('T')[0] : ''
  )
  const [saving, setSaving] = useState(false)

  async function handleSave() {
    const trimTitle = title.trim()
    const trimDesc = description.trim()
    if (!trimTitle || !trimDesc) return
    setSaving(true)
    try {
      const patch = { title: trimTitle, description: trimDesc, due_date: dueDate || null }
      await patchWorkspace(workspaceId, patch)
      onWorkspaceUpdate({ title: trimTitle, description: trimDesc, dueDate: dueDate || null })
    } catch (err) {
      alert(err.detail ?? 'Could not save changes')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-tab">
      <section className="settings-section">
        <h2 className="settings-section__title">General</h2>

        <div className="settings-field">
          <label className="settings-field__label">Name</label>
          {isAdmin
            ? <input className="settings-field__input" value={title} onChange={(e) => setTitle(e.target.value)} />
            : <p className="settings-field__value">{workspace.title}</p>
          }
        </div>

        <div className="settings-field">
          <label className="settings-field__label">Description</label>
          {isAdmin
            ? <textarea className="settings-field__textarea" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
            : <p className="settings-field__value">{workspace.description}</p>
          }
        </div>

        <div className="settings-field">
          <label className="settings-field__label">Due date</label>
          {isAdmin
            ? <input type="date" className="settings-field__input" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            : <p className="settings-field__value">{workspace.dueDate ? formatDueDate(workspace.dueDate) : 'No due date'}</p>
          }
        </div>

        {isAdmin && (
          <button type="button" className="settings-save-btn" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        )}
      </section>

      <section className="settings-section settings-section--danger">
        <h2 className="settings-section__title">Danger zone</h2>

        <div className="settings-danger-row">
          <div>
            <p className="settings-danger-label">Leave workspace</p>
            <p className="settings-danger-desc">You will lose access to all tasks and discussions.</p>
          </div>
          <button type="button" className="settings-danger-btn" onClick={onLeave}>Leave</button>
        </div>

        {isAdmin && (
          <div className="settings-danger-row">
            <div>
              <p className="settings-danger-label">Archive workspace</p>
              <p className="settings-danger-desc">Hides this workspace from the active list. Can be restored.</p>
            </div>
            <button type="button" className="settings-danger-btn"
              onClick={() => patchWorkspace(workspaceId, { is_archived: true }).catch(() => {})}>
              Archive
            </button>
          </div>
        )}
        {isCreator && (
          <div className="settings-danger-row">
            <div>
              <p className="settings-danger-label">Delete workspace</p>
              <p className="settings-danger-desc">Permanently deletes the workspace and all tasks. Cannot be undone.</p>
            </div>
            <button type="button" className="settings-danger-btn settings-danger-btn--critical" onClick={onDelete}>
              Delete
            </button>
          </div>
        )}
      </section>
    </div>
  )
}

function SlideOver({ task, fullTask, slideOverLoading, workspace, memberById, members, isAdmin, currentUserId, workspaceId, width, onResize, onClose, onToggle, onDelete, onSave, onReassign }) {
  const [editTitle, setEditTitle] = useState(task.title)
  const [editContent, setEditContent] = useState('')
  const [menuOpen, setMenuOpen, menuRef] = useDismissableMenu()

  const widthRef = useRef(width)
  useEffect(() => { widthRef.current = width }, [width])

  useEffect(() => { setEditTitle(task.title) }, [task.id])
  useEffect(() => { setEditContent(fullTask?.content ?? '') }, [fullTask])

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleResizeStart = useCallback((e) => {
    e.preventDefault()
    const startX = e.clientX
    const startW = widthRef.current
    function onMove(ev) {
      const newW = Math.max(320, Math.min(800, startW + (startX - ev.clientX)))
      onResize(newW)
    }
    function onUp() {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [onResize])

  const owner = memberById.get(task.ownerId)
  const isOwner = task.ownerId === currentUserId
  const canReassign = isOwner || isAdmin

  async function handleTitleBlur() {
    const trimmed = editTitle.trim()
    if (!trimmed || trimmed === task.title) return
    await onSave(task.id, { title: trimmed })
  }

  async function handleContentBlur() {
    if (editContent === (fullTask?.content ?? '')) return
    await onSave(task.id, { content: editContent })
  }

  return (
    <>
      <div className="slide-over-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="slide-over" style={{ width }} aria-label="Task details">
        <div className="slide-over__resize-handle" onMouseDown={handleResizeStart} />

        <div className="slide-over__header">
          <span className="slide-over__workspace-name">{workspace.title}</span>
          <div ref={menuRef} className="slide-over__menu-wrap">
            <button type="button" className="slide-over__icon-btn" onClick={() => setMenuOpen((v) => !v)} aria-label="Task actions">
              <DotsIcon />
            </button>
            {menuOpen && (
              <ul className="wd-menu-list" role="menu">
                {isOwner && (
                  <li role="none">
                    <button type="button" role="menuitem" className="wd-menu-item"
                      onClick={() => { onToggle(task.id); setMenuOpen(false) }}>
                      {task.isCompleted ? 'Mark incomplete' : 'Mark complete'}
                    </button>
                  </li>
                )}
                {canReassign && (
                  <li role="none">
                    <button type="button" role="menuitem" className="wd-menu-item"
                      onClick={() => { onReassign(task.id); setMenuOpen(false) }}>
                      Reassign
                    </button>
                  </li>
                )}
                {isAdmin && (
                  <li role="none">
                    <button type="button" role="menuitem" className="wd-menu-item wd-menu-item--danger"
                      onClick={() => { onDelete(task.id); setMenuOpen(false); onClose() }}>
                      Delete
                    </button>
                  </li>
                )}
              </ul>
            )}
          </div>
          <button type="button" className="slide-over__icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="slide-over__body">
          <div className="slide-over__title-row">
            {isOwner ? (
              <button
                type="button"
                className={`slide-over__checkbox${task.isCompleted ? ' slide-over__checkbox--checked' : ''}`}
                onClick={() => onToggle(task.id)}
                aria-label={task.isCompleted ? 'Mark incomplete' : 'Mark complete'}
              >
                {task.isCompleted && <CheckIcon />}
              </button>
            ) : (
              <span className={`slide-over__checkbox slide-over__checkbox--readonly${task.isCompleted ? ' slide-over__checkbox--checked' : ''}`}>
                {task.isCompleted && <CheckIcon />}
              </span>
            )}
            <input
              className={`slide-over__title${task.isCompleted ? ' slide-over__title--completed' : ''}`}
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              onBlur={handleTitleBlur}
              onKeyDown={(e) => { if (e.key === 'Enter') e.target.blur() }}
            />
          </div>

          <dl className="slide-over__fields">
            <div className="slide-over__field">
              <dt className="slide-over__field-label">Owner</dt>
              <dd className="slide-over__field-value">
                {owner
                  ? <><MemberAvatar member={owner} size={20} /><span>{owner.name}</span></>
                  : 'Unassigned'
                }
              </dd>
            </div>
            <div className="slide-over__field">
              <dt className="slide-over__field-label">Due date</dt>
              <dd className="slide-over__field-value">
                <CalIcon />
                <span className={task.dueDate ? `wd-due-text--${getTaskUrgency(task.dueDate)}` : ''}>
                  {task.dueDate ? formatDueDate(task.dueDate) : 'No due date'}
                </span>
              </dd>
            </div>
            <div className="slide-over__field">
              <dt className="slide-over__field-label">Workspace</dt>
              <dd className="slide-over__field-value">{workspace.title}</dd>
            </div>
          </dl>

          <div className="slide-over__section">
            <p className="slide-over__section-label">Description</p>
            {slideOverLoading
              ? <p className="slide-over__muted">Loading…</p>
              : (
                <textarea
                  className="slide-over__content-input"
                  placeholder="Add a description…"
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  onBlur={handleContentBlur}
                  rows={4}
                />
              )
            }
          </div>

          <div className="slide-over__comment-tabs">
            <button type="button" className="wd-tab wd-tab--active" style={{ paddingLeft: 0 }}>Comments</button>
            <button type="button" className="wd-tab">
              Resources <span className="wd-tab__soon">SOON</span>
            </button>
          </div>

          <div className="slide-over__comments-empty">
            <ChatIcon />
            <p>Comments coming soon</p>
          </div>
        </div>
      </aside>
    </>
  )
}

function FloatingActions() {
  return (
    <div className="floating-actions">
      <button type="button" className="floating-actions__btn floating-actions__btn--filobelo">
        <SparkleIcon />
        <span>Ask Filobelo · AI assistant</span>
      </button>
      <button type="button" className="floating-actions__btn floating-actions__btn--chat">
        <ChatIcon />
        <span>Workspace chat coming soon</span>
      </button>
    </div>
  )
}

// ─── main component ─────────────────────────────────────────────────────────

const URGENCY_COLOR = {
  error:   'var(--color-error)',
  warning: 'var(--color-warning)',
  success: 'var(--color-success)',
  neutral: 'var(--color-neutral)',
}

const TABS = [
  { id: 'tasks',    label: 'Tasks' },
  { id: 'members',  label: 'Members' },
  { id: 'kanban',   label: 'Kanban',  soon: true },
  { id: 'settings', label: 'Settings' },
]

function WorkspaceDetail() {
  const { id } = useParams()
  const workspaceId = parseInt(id, 10)
  const { user } = useAuth()
  const navigate = useNavigate()
  const { onDelete: shellDelete, onLeave: shellLeave } = useOutletContext()
  const currentUserId = user?.id

  const [workspace, setWorkspace]               = useState(null)
  const [tasks, setTasks]                       = useState([])
  const [loading, setLoading]                   = useState(true)
  const [error, setError]                       = useState(null)
  const [activeTab, setActiveTab]               = useState('tasks')
  const [completedOpen, setCompletedOpen]       = useState(false)
  const [selectedTaskId, setSelectedTaskId]     = useState(null)
  const [slideOverTask, setSlideOverTask]       = useState(null)
  const [slideOverLoading, setSlideOverLoading] = useState(false)
  const [slideOverWidth, setSlideOverWidth]     = useState(420)
  const [showInlineAdd, setShowInlineAdd]       = useState(false)
  const [inlineAddTitle, setInlineAddTitle]     = useState('')
  const [detailMembers, setDetailMembers]       = useState(null)
  const [membersLoading, setMembersLoading]     = useState(false)
  const [reassignTaskId, setReassignTaskId]     = useState(null)

  useEffect(() => {
    async function load() {
      setLoading(true)
      setError(null)
      setSelectedTaskId(null)
      setSlideOverTask(null)
      setDetailMembers(null)
      try {
        const data = await getWorkspace(workspaceId)
        setWorkspace(normalizeWorkspace(data))
        setTasks((data.tasks ?? []).map(normalizeTask))
      } catch (err) {
        setError(err.detail ?? 'Could not load workspace')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [workspaceId])

  async function loadDetailMembers() {
    if (detailMembers !== null || membersLoading) return
    setMembersLoading(true)
    try {
      const data = await getMembersWithRoles(workspaceId)
      setDetailMembers(data.map((m) => ({
        id: m.id,
        name: m.username,
        avatarUrl: toAvatarUrl(m.image_path),
        role: m.role,
      })))
    } catch {
      // fall back silently — basic member list shown
    } finally {
      setMembersLoading(false)
    }
  }

  function handleTabChange(tabId) {
    setActiveTab(tabId)
    if (tabId === 'members') loadDetailMembers()
  }

  async function handleSelectTask(taskId) {
    setSelectedTaskId(taskId)
    setSlideOverTask(null)
    setSlideOverLoading(true)
    try {
      const data = await authFetch(`/workspaces/${workspaceId}/tasks/${taskId}`)
      setSlideOverTask(data)
    } catch {
      // slide-over opens without description
    } finally {
      setSlideOverLoading(false)
    }
  }

  function handleCloseSlideOver() {
    setSelectedTaskId(null)
    setSlideOverTask(null)
  }

  async function handleToggleTask(taskId) {
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return
    const next = !task.isCompleted
    setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, isCompleted: next } : t))
    try {
      await toggleTask(workspaceId, taskId)
    } catch {
      setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, isCompleted: task.isCompleted } : t))
    }
  }

  async function handleAddTask() {
    const title = inlineAddTitle.trim()
    if (!title) return
    setInlineAddTitle('')
    setShowInlineAdd(false)
    try {
      const data = await createTask(workspaceId, { title })
      setTasks((prev) => [normalizeTask(data), ...prev])
    } catch (err) {
      alert(err.detail ?? 'Could not create task')
    }
  }

  async function handleDeleteTask(taskId) {
    setTasks((prev) => prev.filter((t) => t.id !== taskId))
    if (selectedTaskId === taskId) handleCloseSlideOver()
    try {
      await deleteTask(workspaceId, taskId)
    } catch (err) {
      alert(err.detail ?? 'Could not delete task')
    }
  }

  async function handleSaveTask(taskId, patch) {
    try {
      await patchTask(workspaceId, taskId, patch)
      setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, ...patch } : t))
      if (patch.content !== undefined) {
        setSlideOverTask((prev) => prev ? { ...prev, content: patch.content } : prev)
      }
    } catch (err) {
      console.error(err)
    }
  }

  async function handleReassignTask(taskId, userId) {
    setReassignTaskId(null)
    try {
      await reassignTask(workspaceId, taskId, userId)
      setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, ownerId: userId } : t))
    } catch (err) {
      alert(err.detail ?? 'Could not reassign task')
    }
  }

  async function handleRemoveMember(userId) {
    const prev = detailMembers
    setDetailMembers((m) => m?.filter((mb) => mb.id !== userId) ?? null)
    try {
      await removeMember(workspaceId, userId)
    } catch (err) {
      setDetailMembers(prev)
      alert(err.detail ?? 'Could not remove member')
    }
  }

  async function handlePromoteToAdmin(userId) {
    try {
      await promoteToAdmin(workspaceId, userId)
      setDetailMembers((prev) => prev?.map((m) => m.id === userId ? { ...m, role: 'admin' } : m) ?? null)
    } catch (err) {
      alert(err.detail ?? 'Could not promote member')
    }
  }

  function handleMemberAdded() {
    // Reload enriched member list after invite
    setDetailMembers(null)
    setMembersLoading(false)
    loadDetailMembers()
  }

  function handleWorkspaceUpdate({ title, description, dueDate }) {
    setWorkspace((prev) => ({ ...prev, title, description, dueDate }))
  }

  async function handleDeleteWorkspace() {
    await shellDelete(workspaceId)
    navigate('/')
  }

  async function handleLeaveWorkspace() {
    await shellLeave(workspaceId)
    navigate('/')
  }

  if (loading) {
    return <div className="workspace-detail workspace-detail--state"><p>Loading workspace…</p></div>
  }
  if (error) {
    return <div className="workspace-detail workspace-detail--state workspace-detail--error"><p>{error}</p></div>
  }
  if (!workspace) return null

  // Derived
  const activeTasks       = tasks.filter((t) => !t.isCompleted)
  const completedTasks    = tasks.filter((t) => t.isCompleted)
  const overdueCount      = activeTasks.filter((t) => getDaysRemaining(t.dueDate) < 0).length
  const dueThisWeekCount  = activeTasks.filter((t) => {
    const d = getDaysRemaining(t.dueDate)
    return d !== null && d >= 0 && d <= 7
  }).length
  const localProgress     = tasks.length > 0
    ? Math.round((completedTasks.length / tasks.length) * 100)
    : 0
  const urgency           = getWorkspaceUrgency({ dueDate: workspace.dueDate, progress: localProgress })
  const progressColor     = URGENCY_COLOR[urgency] ?? 'var(--color-brand-primary)'
  const memberById        = new Map(workspace.members.map((m) => [m.id, m]))
  const isAdmin           = workspace.currentUserRole === 'admin'
  const isCreator         = workspace.creatorId === currentUserId
  const sortedActiveTasks = sortByUrgency(activeTasks)
  const selectedTask      = tasks.find((t) => t.id === selectedTaskId) ?? null
  const displayMembers    = detailMembers ?? workspace.members.map((m) => ({ ...m, role: null }))
  const reassignTask_     = tasks.find((t) => t.id === reassignTaskId) ?? null

  const initials = workspace.title
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('')

  return (
    <div className="workspace-detail">
      {/* ── Header ── */}
      <header className="wd-header">
        <nav className="wd-breadcrumb" aria-label="Breadcrumb">
          <Link to="/" className="wd-breadcrumb__link">All workspaces</Link>
          <span className="wd-breadcrumb__sep" aria-hidden="true">›</span>
          <span className="wd-breadcrumb__current">{workspace.title}</span>
        </nav>

        <div className="wd-header__main">
          <div className="wd-header__avatar" aria-hidden="true">{initials}</div>

          <div className="wd-header__info">
            <div className="wd-header__title-row">
              <h1 className="wd-header__title">{workspace.title}</h1>
              {workspace.dueDate && localProgress < 100 && (
                <span className={`wd-urgency-badge wd-urgency-badge--${urgency}`}>
                  {formatDueDate(workspace.dueDate)}
                </span>
              )}
            </div>
            <p className="wd-header__description">{workspace.description}</p>
          </div>

          <div className="wd-header__side">
            <div className="wd-header__member-stack">
              {workspace.members.slice(0, 3).map((m) => (
                <MemberAvatar key={m.id} member={m} size={30} />
              ))}
              {workspace.members.length > 3 && (
                <span className="member-avatar member-avatar--overflow" style={{ width: 30, height: 30, fontSize: 11 }}>
                  +{workspace.members.length - 3}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="wd-header__progress">
          <div className="wd-header__progress-track">
            <div
              className="wd-header__progress-fill"
              style={{ width: `${localProgress}%`, backgroundColor: progressColor }}
            />
          </div>
          <span className="wd-header__progress-pct">{localProgress}%</span>
        </div>
      </header>

      {/* ── Tabs ── */}
      <div className="wd-tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`wd-tab${activeTab === tab.id ? ' wd-tab--active' : ''}`}
            onClick={() => handleTabChange(tab.id)}
          >
            {tab.label}
            {tab.soon && <span className="wd-tab__soon">SOON</span>}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <div className="wd-content">

        {/* Tasks tab */}
        {activeTab === 'tasks' && (
          <div className="tasks-tab">
            <div className="tasks-tab__summary">
              <span className="tasks-tab__count">
                {completedTasks.length} of {tasks.length} task{tasks.length !== 1 ? 's' : ''} complete
              </span>
              {overdueCount > 0 && (
                <span className="task-pill task-pill--error">● {overdueCount} overdue</span>
              )}
              {dueThisWeekCount > 0 && (
                <span className="task-pill task-pill--warning">● {dueThisWeekCount} due this week</span>
              )}
              <button type="button" className="tasks-tab__add-btn" onClick={() => setShowInlineAdd(true)}>
                + Add task
              </button>
            </div>

            <div className="task-list">
              {sortedActiveTasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  member={memberById.get(task.ownerId)}
                  isAdmin={isAdmin}
                  currentUserId={currentUserId}
                  onSelect={() => handleSelectTask(task.id)}
                  onToggle={() => handleToggleTask(task.id)}
                  onReassign={() => setReassignTaskId(task.id)}
                  onDelete={() => handleDeleteTask(task.id)}
                />
              ))}

              {showInlineAdd ? (
                <div className="inline-add">
                  <span className="inline-add__checkbox" aria-hidden="true" />
                  <input
                    className="inline-add__input"
                    placeholder="Task title…"
                    value={inlineAddTitle}
                    onChange={(e) => setInlineAddTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAddTask()
                      if (e.key === 'Escape') { setShowInlineAdd(false); setInlineAddTitle('') }
                    }}
                    onBlur={() => {
                      if (!inlineAddTitle.trim()) { setShowInlineAdd(false); setInlineAddTitle('') }
                    }}
                    autoFocus
                  />
                  <button type="button" className="inline-add__submit" onClick={handleAddTask}>Add</button>
                  <button type="button" className="inline-add__cancel"
                    onClick={() => { setShowInlineAdd(false); setInlineAddTitle('') }}>✕</button>
                </div>
              ) : (
                <button type="button" className="inline-add-trigger" onClick={() => setShowInlineAdd(true)}>
                  + Add a task…
                </button>
              )}
            </div>

            {completedTasks.length > 0 && (
              <div className="completed-section">
                <button type="button" className="completed-section__toggle"
                  onClick={() => setCompletedOpen((v) => !v)}>
                  <span className="completed-section__arrow">{completedOpen ? '▼' : '▶'}</span>
                  COMPLETED {completedTasks.length}
                </button>
                {completedOpen && (
                  <div className="task-list task-list--completed">
                    {completedTasks.map((task) => (
                      <TaskRow
                        key={task.id}
                        task={task}
                        member={memberById.get(task.ownerId)}
                        isAdmin={isAdmin}
                        currentUserId={currentUserId}
                        onSelect={() => handleSelectTask(task.id)}
                        onToggle={() => handleToggleTask(task.id)}
                        onReassign={() => setReassignTaskId(task.id)}
                        onDelete={() => handleDeleteTask(task.id)}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Members tab */}
        {activeTab === 'members' && (
          <div className="members-tab">
            {isAdmin && (
              <InvitePanel workspaceId={workspaceId} onMemberAdded={handleMemberAdded} />
            )}
            {membersLoading && !detailMembers && (
              <p className="members-tab__loading">Loading members…</p>
            )}
            <ul className="members-list">
              {displayMembers.map((m) => (
                <MemberListRow
                  key={m.id}
                  member={m}
                  isAdmin={isAdmin}
                  isSelf={m.id === currentUserId}
                  onRemove={handleRemoveMember}
                  onPromote={handlePromoteToAdmin}
                  onLeave={handleLeaveWorkspace}
                />
              ))}
            </ul>
          </div>
        )}

        {activeTab === 'kanban' && (
          <div className="soon-placeholder"><p>Kanban view coming soon</p></div>
        )}

        {activeTab === 'settings' && (
          <SettingsTab
            workspace={workspace}
            isAdmin={isAdmin}
            isCreator={isCreator}
            workspaceId={workspaceId}
            onWorkspaceUpdate={handleWorkspaceUpdate}
            onDelete={handleDeleteWorkspace}
            onLeave={handleLeaveWorkspace}
          />
        )}
      </div>

      {/* ── Slide-over ── */}
      {selectedTask && (
        <SlideOver
          task={selectedTask}
          fullTask={slideOverTask}
          slideOverLoading={slideOverLoading}
          workspace={workspace}
          memberById={memberById}
          members={workspace.members}
          isAdmin={isAdmin}
          currentUserId={currentUserId}
          workspaceId={workspaceId}
          width={slideOverWidth}
          onResize={setSlideOverWidth}
          onClose={handleCloseSlideOver}
          onToggle={handleToggleTask}
          onDelete={handleDeleteTask}
          onSave={handleSaveTask}
          onReassign={(taskId) => setReassignTaskId(taskId)}
        />
      )}

      {/* ── Member picker (reassign) ── */}
      {reassignTask_ && (
        <MemberPicker
          members={workspace.members}
          currentOwnerId={reassignTask_.ownerId}
          onSelect={(userId) => handleReassignTask(reassignTaskId, userId)}
          onClose={() => setReassignTaskId(null)}
        />
      )}

      {/* ── Floating actions ── */}
      <FloatingActions />
    </div>
  )
}

export default WorkspaceDetail
