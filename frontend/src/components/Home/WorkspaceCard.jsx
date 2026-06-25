import { getWorkspaceStatus, isWorkspaceLate, WORKSPACE_STATUS } from '../../utils/workspaceStatus'
import { formatDueDate } from '../../utils/date'
import './WorkspaceCard.css'

const PROGRESS_COLOR_VAR = {
  [WORKSPACE_STATUS.NOT_STARTED]: 'var(--color-text-muted)',
  [WORKSPACE_STATUS.IN_PROGRESS]: 'var(--color-info)',
  [WORKSPACE_STATUS.COMPLETE]: 'var(--color-success)',
}

function WorkspaceCard({ workspace, members, onSelect }) {
  const status = getWorkspaceStatus(workspace)
  const late = isWorkspaceLate(workspace)
  const progressColor = late ? 'var(--color-error)' : PROGRESS_COLOR_VAR[status]
  const visibleMembers = members?.slice(0, 3) ?? []
  const overflowCount = members ? Math.max(members.length - 3, 0) : 0

  return (
    <button
      type="button"
      className="workspace-card"
      onClick={() => onSelect?.(workspace.id)}
    >
      <div className="workspace-card__progress-track">
        <div
          className="workspace-card__progress-fill"
          style={{
            width: `${workspace.progress ?? 0}%`,
            backgroundColor: progressColor,
          }}
        />
      </div>

      <div className="workspace-card__body">
        <h3 className="workspace-card__title">{workspace.title}</h3>

        <div className="workspace-card__meta">
          <span
            className={`workspace-card__due${late ? ' workspace-card__due--late' : ''}`}
          >
            {formatDueDate(workspace.dueDate)}
          </span>
          <span className="workspace-card__progress-label">
            {Math.round(workspace.progress ?? 0)}%
          </span>
        </div>

        <div className="workspace-card__footer">
          <span className="workspace-card__task-count">
            {workspace.numOfTasks ?? 0} task{workspace.numOfTasks === 1 ? '' : 's'}
          </span>

          {members ? (
            <span className="workspace-card__avatars">
              {visibleMembers.map((member) => (
                <span key={member.id} className="workspace-card__avatar">
                  {member.avatarUrl ? (
                    <img src={member.avatarUrl} alt="" />
                  ) : (
                    member.name?.[0]?.toUpperCase() ?? '?'
                  )}
                </span>
              ))}
              {overflowCount > 0 && (
                <span className="workspace-card__avatar workspace-card__avatar--overflow">
                  +{overflowCount}
                </span>
              )}
            </span>
          ) : (
            <span className="workspace-card__member-count">
              {workspace.numOfMembers ?? 0} member
              {workspace.numOfMembers === 1 ? '' : 's'}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

export default WorkspaceCard
