import { getDaysRemaining } from './date'

export const WORKSPACE_STATUS = {
  NOT_STARTED: 'not-started',
  IN_PROGRESS: 'in-progress',
  COMPLETE: 'complete',
}

/** Base lifecycle state, derived from task count/progress alone —
 * no start date needed. */
export function getWorkspaceStatus({ numOfTasks = 0, progress = 0 }) {
  if (numOfTasks === 0) return WORKSPACE_STATUS.NOT_STARTED
  if (progress >= 100) return WORKSPACE_STATUS.COMPLETE
  return WORKSPACE_STATUS.IN_PROGRESS
}

/** Late is an overlay, not a 4th status — a workspace can be late while
 * not-started or in-progress. Approximated from the workspace due date
 * only (no per-task due dates available at the list level yet). */
export function isWorkspaceLate({ dueDate, progress = 0 }) {
  if (!dueDate || progress >= 100) return false
  return new Date(dueDate).getTime() < Date.now()
}

/** Active = not explicitly completed, not archived. Uses the is_completed flag. */
export function getActiveWorkspaces(workspaces) {
  return workspaces.filter((ws) => !ws.isArchived && !ws.isCompleted)
}

/** Single urgency level for a workspace — drives status dot and card accent.
 *  error = overdue, warning = due ≤3d, success = has deadline and on track, neutral = no deadline */
export function getWorkspaceUrgency(workspace) {
  if (isWorkspaceLate(workspace)) return 'error'
  const days = getDaysRemaining(workspace.dueDate)
  if (days !== null && days <= 3) return 'warning'
  if (days === null) return 'neutral'
  return 'success'
}

/** Overdue first, then soonest due date, no-deadline workspaces last. */
export function sortByUrgency(workspaces) {
  return [...workspaces].sort((a, b) => {
    if (!a.dueDate && !b.dueDate) return 0
    if (!a.dueDate) return 1
    if (!b.dueDate) return -1
    return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()
  })
}
