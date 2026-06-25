const MS_PER_DAY = 1000 * 60 * 60 * 24

/** Whole days remaining until dueDate; negative if overdue. */
export function getDaysRemaining(dueDate) {
  if (!dueDate) return null
  const diff = new Date(dueDate).getTime() - Date.now()
  return Math.ceil(diff / MS_PER_DAY)
}

export function formatDueDate(dueDate) {
  if (!dueDate) return 'No deadline'

  const days = getDaysRemaining(dueDate)
  if (days < 0) return `${Math.abs(days)}d overdue`
  if (days === 0) return 'Due today'
  if (days === 1) return 'Due tomorrow'
  return `${days}d left`
}
