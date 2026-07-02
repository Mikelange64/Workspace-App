import WorkspaceCard from './WorkspaceCard'
import NewWorkspaceCard from './NewWorkspaceCard'
import EmptyState from './EmptyState'
import { getActiveWorkspaces, sortByUrgency } from '../../utils/workspaceStatus'
import './WorkspaceGrid.css'

const GRID_SIZE = 6

function WorkspaceGrid({ workspaces, membersByWorkspaceId, onSelectWorkspace, onNewWorkspace, onComplete, mascotSlot }) {
  const active = sortByUrgency(getActiveWorkspaces(workspaces))

  if (active.length === 0) {
    return <EmptyState mascotSlot={mascotSlot} onNewWorkspace={onNewWorkspace} />
  }

  const visible = active.slice(0, GRID_SIZE)
  const remaining = active.length - visible.length
  const showGhostCard = visible.length < GRID_SIZE

  return (
    <div className="workspace-grid-section">
      <div className="workspace-grid">
        {visible.map((ws) => (
          <WorkspaceCard
            key={ws.id}
            workspace={ws}
            members={ws.members ?? membersByWorkspaceId?.[ws.id]}
            onSelect={onSelectWorkspace}
            onComplete={onComplete}
          />
        ))}
        {showGhostCard && <NewWorkspaceCard onClick={onNewWorkspace} />}
      </div>

      {remaining > 0 && (
        <p className="workspace-grid__more">+{remaining} more active</p>
      )}
    </div>
  )
}

export default WorkspaceGrid
