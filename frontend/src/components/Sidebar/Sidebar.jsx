import { useState, useRef, useEffect } from 'react'
import WorkspaceListItem from './WorkspaceListItem'
import './Sidebar.css'

const FOLDER_COLORS = [
  '#ecf79e', '#98af57', '#5bbf8a', '#6bc4d4',
  '#6970f4', '#a78bf5', '#f9b3e4', '#fc556e',
  '#f9b53e', '#f4a26a', '#b0c4de', '#c9b99a',
]

function FolderIcon({ color, open }) {
  return open ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill={color} stroke={color} strokeWidth="0" aria-hidden="true">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" opacity="0.9"/>
    </svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill={color} stroke={color} strokeWidth="0" aria-hidden="true">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" opacity="0.6"/>
    </svg>
  )
}

function ChevronIcon({ open }) {
  return (
    <svg
      width="12" height="12" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2.5"
      style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.15s' }}
      aria-hidden="true"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

function ColorPicker({ selected, onChange }) {
  return (
    <div className="sidebar__color-picker">
      {FOLDER_COLORS.map((color) => (
        <button
          key={color}
          type="button"
          className={`sidebar__color-swatch${selected === color ? ' sidebar__color-swatch--active' : ''}`}
          style={{ backgroundColor: color }}
          onClick={() => onChange(color)}
          aria-label={color}
        />
      ))}
    </div>
  )
}

function FolderCreateRow({ onCreate, onCancel }) {
  const [name, setName] = useState('')
  const [color, setColor] = useState(FOLDER_COLORS[0])
  const [showPicker, setShowPicker] = useState(false)
  const inputRef = useRef(null)
  const pickerRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  useEffect(() => {
    if (!showPicker) return
    function handleClickOutside(e) {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) setShowPicker(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showPicker])

  function handleKeyDown(e) {
    if (e.key === 'Enter') submit()
    if (e.key === 'Escape') onCancel()
  }

  function submit() {
    const trimmed = name.trim()
    if (!trimmed) return
    onCreate(trimmed, color)
  }

  return (
    <div className="sidebar__folder-create">
      <div className="sidebar__folder-create-row">
        <div className="sidebar__color-dot-wrap" ref={pickerRef}>
          <button
            type="button"
            className="sidebar__color-dot"
            style={{ backgroundColor: color }}
            onClick={() => setShowPicker((v) => !v)}
            aria-label="Choose folder color"
          />
          {showPicker && (
            <ColorPicker selected={color} onChange={(c) => { setColor(c); setShowPicker(false) }} />
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          className="sidebar__folder-input"
          placeholder="Folder name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={handleKeyDown}
          maxLength={50}
        />
        <button type="button" className="sidebar__folder-confirm" onClick={submit} aria-label="Create folder">✓</button>
        <button type="button" className="sidebar__folder-cancel" onClick={onCancel} aria-label="Cancel">✕</button>
      </div>
    </div>
  )
}

function FolderItem({ folder, workspaces, folders, onDelete, onSelectWorkspace, onTogglePin, onArchive, onLeave, onDeleteWorkspace, onMoveToFolder }) {
  const [expanded, setExpanded] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  return (
    <div className="sidebar__folder">
      <div className="sidebar__folder-row">
        <button
          type="button"
          className="sidebar__folder-toggle"
          onClick={() => setExpanded((v) => !v)}
        >
          <FolderIcon color={folder.color} open={expanded} />
          <span className="sidebar__folder-name">{folder.name}</span>
          <span className="sidebar__folder-chevron">
            <ChevronIcon open={expanded} />
          </span>
        </button>

        <div className="sidebar__folder-menu-wrap" ref={menuRef}>
          <button
            type="button"
            className="sidebar__folder-menu-btn"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Folder options"
          >
            <DotsIcon />
          </button>
          {menuOpen && (
            <ul className="sidebar__folder-menu">
              <li>
                <button type="button" onClick={() => { onDelete(folder.id); setMenuOpen(false) }}>
                  Delete folder
                </button>
              </li>
            </ul>
          )}
        </div>
      </div>

      {expanded && workspaces.length > 0 && (
        <div className="sidebar__folder-children">
          {workspaces.map((ws) => (
            <WorkspaceListItem
              key={ws.id}
              workspace={ws}
              folders={folders}
              onSelect={onSelectWorkspace}
              onTogglePin={onTogglePin}
              onArchive={onArchive}
              onLeave={onLeave}
              onDelete={onDeleteWorkspace}
              onMoveToFolder={onMoveToFolder}
            />
          ))}
        </div>
      )}

      {expanded && workspaces.length === 0 && (
        <p className="sidebar__folder-empty">No workspaces</p>
      )}
    </div>
  )
}

function DotsIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
      <circle cx="5" cy="12" r="1.6" fill="currentColor" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" />
      <circle cx="19" cy="12" r="1.6" fill="currentColor" />
    </svg>
  )
}

function byMostRecent(a, b) {
  return new Date(b.dateCreated).getTime() - new Date(a.dateCreated).getTime()
}

function Sidebar({
  workspaces = [],
  completedCount = 0,
  folders = [],
  currentUser = null,
  onNewWorkspace,
  onOpenInbox,
  onOpenCompleted,
  onSelectWorkspace,
  onTogglePin,
  onArchive,
  onLeave,
  onDelete,
  onCreateFolder,
  onDeleteFolder,
  onMoveToFolder,
  onProfileClick,
}) {
  const [creatingFolder, setCreatingFolder] = useState(false)

  const pinned = workspaces.filter((ws) => ws.isPinned).sort(byMostRecent)
  const rest = workspaces.filter((ws) => !ws.isPinned).sort(byMostRecent)

  async function handleCreate(name, color) {
    try {
      await onCreateFolder(name, color)
    } catch (err) {
      console.error(err)
    } finally {
      setCreatingFolder(false)
    }
  }

  return (
    <nav className="sidebar" aria-label="Workspaces">
      <div className="sidebar__actions">
        <button type="button" className="sidebar__action sidebar__action--primary" onClick={onNewWorkspace}>
          + New workspace
        </button>
        <button type="button" className="sidebar__action sidebar__action--muted" onClick={onOpenInbox}>
          Inbox
        </button>
      </div>

      <div className="sidebar__list">
        {/* Folders */}
        <div className="sidebar__section">
          <div className="sidebar__section-header">
            <h2 className="sidebar__section-label">Folders</h2>
            <button
              type="button"
              className="sidebar__section-add"
              onClick={() => setCreatingFolder(true)}
              aria-label="New folder"
            >
              +
            </button>
          </div>

          {creatingFolder && (
            <FolderCreateRow onCreate={handleCreate} onCancel={() => setCreatingFolder(false)} />
          )}

          {folders.length === 0 && !creatingFolder && (
            <p className="sidebar__empty-hint">No folders yet</p>
          )}

          {folders.map((folder) => (
            <FolderItem
              key={folder.id}
              folder={folder}
              workspaces={workspaces.filter((ws) => ws.folderId === folder.id).sort(byMostRecent)}
              folders={folders}
              onDelete={onDeleteFolder}
              onSelectWorkspace={onSelectWorkspace}
              onTogglePin={onTogglePin}
              onArchive={onArchive}
              onLeave={onLeave}
              onDeleteWorkspace={onDelete}
              onMoveToFolder={onMoveToFolder}
            />
          ))}
        </div>

        <div className="sidebar__divider" />

        {workspaces.length === 0 ? (
          <p className="sidebar__empty">No workspaces yet.</p>
        ) : (
          <>
            {pinned.length > 0 && (
              <>
                <div className="sidebar__section">
                  <h2 className="sidebar__section-label">Pinned</h2>
                  {pinned.map((ws) => (
                    <WorkspaceListItem
                      key={ws.id}
                      workspace={ws}
                      folders={folders}
                      folderColor={folders.find((f) => f.id === ws.folderId)?.color}
                      onSelect={onSelectWorkspace}
                      onTogglePin={onTogglePin}
                      onArchive={onArchive}
                      onLeave={onLeave}
                      onDelete={onDelete}
                      onMoveToFolder={onMoveToFolder}
                    />
                  ))}
                </div>
                <div className="sidebar__divider" />
              </>
            )}

            <div className="sidebar__section">
              <h2 className="sidebar__section-label">All workspaces</h2>
              {rest.map((ws) => (
                <WorkspaceListItem
                  key={ws.id}
                  workspace={ws}
                  folders={folders}
                  folderColor={folders.find((f) => f.id === ws.folderId)?.color}
                  onSelect={onSelectWorkspace}
                  onTogglePin={onTogglePin}
                  onArchive={onArchive}
                  onLeave={onLeave}
                  onDelete={onDelete}
                  onMoveToFolder={onMoveToFolder}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {completedCount > 0 && (
        <>
          <div className="sidebar__divider" />
          <button type="button" className="sidebar__completed-btn" onClick={onOpenCompleted}>
            <span className="sidebar__completed-label">Completed</span>
            <span className="sidebar__completed-count">{completedCount}</span>
          </button>
        </>
      )}

      <div className="sidebar__footer">
        <button type="button" className="sidebar__profile" onClick={onProfileClick}>
          {currentUser?.avatarUrl ? (
            <img src={currentUser.avatarUrl} alt="" className="sidebar__profile-avatar-img" />
          ) : (
            <span className="sidebar__profile-avatar-placeholder">
              {currentUser?.name ? currentUser.name[0].toUpperCase() : '?'}
            </span>
          )}
          <span className="sidebar__profile-name">{currentUser?.name ?? 'Sign in'}</span>
        </button>
      </div>
    </nav>
  )
}

export default Sidebar
