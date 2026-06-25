import StatusDot from '../shared/StatusDot'
import { formatDueDate } from '../../utils/date'
import './ComingUpSection.css'

function byDueDate(a, b) {
  return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()
}

function ComingUpSection({ tasks = [], onSelectTask }) {
  if (tasks.length === 0) return null

  const sorted = [...tasks].sort(byDueDate)

  return (
    <section className="coming-up" aria-label="Coming up">
      <h2 className="coming-up__heading">Coming up</h2>
      <ul className="coming-up__list">
        {sorted.map((task) => {
          const overdue = new Date(task.dueDate).getTime() < Date.now()
          return (
            <li key={task.id}>
              <button
                type="button"
                className="coming-up__item"
                onClick={() => onSelectTask?.(task.id)}
              >
                <StatusDot status={task.workspaceStatus} late={overdue} />
                <span className="coming-up__title">{task.title}</span>
                <span className="coming-up__workspace">
                  {task.workspaceTitle}
                </span>
                <span
                  className={`coming-up__due${overdue ? ' coming-up__due--late' : ''}`}
                >
                  {formatDueDate(task.dueDate)}
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
