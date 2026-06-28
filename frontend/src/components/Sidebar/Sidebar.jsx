import WorkspaceListItem from './WorkspaceListItem'
import './Sidebar.css'

function byMostRecent(a, b) {
  return new Date(b.dateCreated).getTime() - new Date(a.dateCreated).getTime()
}

function Sidebar({
  workspaces = [],
  currentUser = null,
  onNewWorkspace,
  onOpenInbox,
  onOpenKanbanOverview,
  onSelectWorkspace,
  onTogglePin,
  onArchive,
  onLeave,
  onDelete,
  onProfileClick,
}) {
  const pinned = workspaces.filter((ws) => ws.isPinned).sort(byMostRecent)
  const rest = workspaces.filter((ws) => !ws.isPinned).sort(byMostRecent)

  return (
    <nav className="sidebar" aria-label="Workspaces">
      <div className="sidebar__actions">
        <button
          type="button"
          className="sidebar__action sidebar__action--primary"
          onClick={onNewWorkspace}
        >
          + New workspace
        </button>
        <button
          type="button"
          className="sidebar__action sidebar__action--muted"
          onClick={onOpenInbox}
        >
          Inbox
        </button>
        <button
          type="button"
          className="sidebar__action sidebar__action--muted"
          onClick={onOpenKanbanOverview}
        >
          Kanban overview
        </button>
      </div>

      <div className="sidebar__list">
        {workspaces.length === 0 ? (
          <p className="sidebar__empty">No workspaces yet.</p>
        ) : (
          <>
            {pinned.length > 0 && (
              <div className="sidebar__section">
                <h2 className="sidebar__section-label">Pinned</h2>
                {pinned.map((ws) => (
                  <WorkspaceListItem
                    key={ws.id}
                    workspace={ws}
                    onSelect={onSelectWorkspace}
                    onTogglePin={onTogglePin}
                    onArchive={onArchive}
                    onLeave={onLeave}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            )}

            <div className="sidebar__section">
              {pinned.length > 0 && (
                <h2 className="sidebar__section-label">All workspaces</h2>
              )}
              {rest.map((ws) => (
                <WorkspaceListItem
                  key={ws.id}
                  workspace={ws}
                  onSelect={onSelectWorkspace}
                  onTogglePin={onTogglePin}
                  onArchive={onArchive}
                  onDelete={onDelete}
                />
              ))}
            </div>
          </>
        )}
      </div>

      <div className="sidebar__footer">
        <button
          type="button"
          className="sidebar__profile"
          onClick={onProfileClick}
        >
          {currentUser?.avatarUrl ? (
            <img
              src={currentUser.avatarUrl}
              alt=""
              className="sidebar__profile-avatar-img"
            />
          ) : (
            <span className="sidebar__profile-avatar-placeholder">
              {currentUser?.name ? currentUser.name[0].toUpperCase() : '?'}
            </span>
          )}
          <span className="sidebar__profile-name">
            {currentUser?.name ?? 'Sign in'}
          </span>
        </button>

      </div>
    </nav>
  )
}

export default Sidebar
