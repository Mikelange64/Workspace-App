import { WORKSPACE_STATUS } from '../../utils/workspaceStatus'
import './StatusDot.css'

const STATUS_LABELS = {
  [WORKSPACE_STATUS.NOT_STARTED]: 'Not started',
  [WORKSPACE_STATUS.IN_PROGRESS]: 'In progress',
  [WORKSPACE_STATUS.COMPLETE]: 'Complete',
}

function StatusDot({ status, late = false }) {
  const label = late ? `${STATUS_LABELS[status]} (late)` : STATUS_LABELS[status]

  return (
    <span className="status-dot-group" title={label}>
      <span className={`status-dot status-dot--${status}`} aria-hidden="true" />
      {late && <span className="status-dot status-dot--late" aria-hidden="true" />}
      <span className="status-dot__sr-label">{label}</span>
    </span>
  )
}

export default StatusDot
