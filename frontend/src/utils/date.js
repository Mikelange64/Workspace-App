const MS_PER_DAY = 1000 * 60 * 60 * 24

const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

/** Returns "Jun 28" or "Jun 28, 2025" if the year differs from current year. */
export function formatAbsoluteDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const month = MONTH_ABBR[d.getMonth()]
  const day = d.getDate()
  const year = d.getFullYear()
  return year === new Date().getFullYear()
    ? `${month} ${day}`
    : `${month} ${day}, ${year}`
}

const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

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
  if (days <= 7) {
    const jsDow = (d) => new Date(d).getDay()
    // Remap to Mon=0…Sun=6 so Sunday sorts after Saturday, not before Monday
    const isoDow = (d) => (jsDow(d) + 6) % 7
    const dayName = DAY_NAMES[jsDow(dueDate)]
    return isoDow(dueDate) > isoDow(Date.now())
      ? `Due ${dayName}`
      : `Due next ${dayName}`
  }
  return `${days}d left`
}
