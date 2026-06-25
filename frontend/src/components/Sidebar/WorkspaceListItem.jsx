import useDismissableMenu from '../../hooks/useDismissableMenu'
import StatusDot from '../shared/StatusDot'
import { getWorkspaceStatus, isWorkspaceLate } from '../../utils/workspaceStatus'
import './WorkspaceListItem.css'

function WorkspaceListItem({
  workspace,
  onSelect,
  onTogglePin,
  onArchive,
  onDelete,
}) {
  const [menuOpen, setMenuOpen, menuRef] = useDismissableMenu()
  const status = getWorkspaceStatus(workspace)
  const late = isWorkspaceLate(workspace)
  const canDelete = workspace.currentUserRole === 'admin'

  function handleMenuAction(action) {
    setMenuOpen(false)
    action?.(workspace.id)
  }

  return (
    <div className="workspace-item">
      <button
        type="button"
        className="workspace-item__select"
        onClick={() => onSelect?.(workspace.id)}
      >
        <StatusDot status={status} late={late} />
        <span className="workspace-item__title">{workspace.title}</span>
      </button>

      <div className="workspace-item__menu" ref={menuRef}>
        <button
          type="button"
          className="workspace-item__menu-trigger"
          aria-label={`More actions for ${workspace.title}`}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <DotsIcon />
        </button>

        {menuOpen && (
          <ul className="workspace-item__menu-list" role="menu">
            <li role="none">
              <button
                type="button"
                role="menuitem"
                className="workspace-item__menu-item"
                onClick={() => handleMenuAction(onTogglePin)}
              >
                {workspace.isPinned ? 'Unpin' : 'Pin'}
              </button>
            </li>
            <li role="none">
              <button
                type="button"
                role="menuitem"
                className="workspace-item__menu-item"
                onClick={() => handleMenuAction(onArchive)}
              >
                Archive
              </button>
            </li>
            {canDelete && (
              <li role="none">
                <button
                  type="button"
                  role="menuitem"
                  className="workspace-item__menu-item workspace-item__menu-item--danger"
                  onClick={() => handleMenuAction(onDelete)}
                >
                  Delete
                </button>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
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

export default WorkspaceListItem
