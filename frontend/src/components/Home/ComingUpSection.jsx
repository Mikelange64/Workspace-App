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
  if (!dueDate) return 'neutral'
  const days = getDaysRemaining(dueDate)
  if (days < 0) return 'error'
  if (days <= 3) return 'warning'
  return 'success'
}

function ComingUpSection({ tasks = [], onSelectTask }) {
  if (tasks.length === 0) return null

  const sorted = [...tasks].sort(byDueDate)

  return (
    <section className="coming-up" aria-label="Upcoming tasks">
      <h2 className="coming-up__heading">Upcoming tasks</h2>
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
                <span className="coming-up__content">
                  <span className="coming-up__title">{task.title}</span>
                  <span className="coming-up__workspace">{task.workspaceTitle}</span>
                </span>
                <span className={`coming-up__due coming-up__due--${urgency}`}>
                  {task.dueDate ? formatDueDate(task.dueDate) : 'No deadline'}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

export default ComingUpSection
