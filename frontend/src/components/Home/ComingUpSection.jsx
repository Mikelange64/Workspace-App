import StatusDot from '../shared/StatusDot'
import { getDaysRemaining, formatDueDate } from '../../utils/date'
import './ComingUpSection.css'

function byDueDate(a, b) {
  if (!a.dueDate && !b.dueDate) return 0
  if (!a.dueDate) return 1
  if (!b.dueDate) return -1
  return new Date(a.dueDate) - new Date(b.dueDate)
}

function getTaskUrgency(dueDate) {
  if (!dueDate) return 'success'
  const days = getDaysRemaining(dueDate)
  if (days < 0) return 'error'
  if (days <= 3) return 'warning'
  return 'success'
}

function ComingUpSection({ tasks = [], hasActiveWorkspaces = false, onSelectTask }) {
  if (!hasActiveWorkspaces) return null

  const sorted = [...tasks].sort(byDueDate)

  return (
    <section className="coming-up" aria-label="Upcoming tasks">
      <h2 className="coming-up__heading">Upcoming tasks</h2>

      {sorted.length === 0 ? (
        <p className="coming-up__empty">No tasks yet — add tasks inside a workspace to see them here.</p>
      ) : (
        <ul className="coming-up__list">
          {sorted.map((task) => {
            const urgency = getTaskUrgency(task.dueDate)
            return (
              <li key={task.id}>
                <button
                  type="button"
                  className="coming-up__item"
                  onClick={() => onSelectTask?.(task.id)}
                >
                  <StatusDot urgency={urgency} />
                  <span className="coming-up__title">{task.title}</span>
                  <span className="coming-up__workspace">{task.workspaceTitle}</span>
                  <span className={`coming-up__due coming-up__due--${urgency}`}>
                    {formatDueDate(task.dueDate)}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}

export default ComingUpSection
