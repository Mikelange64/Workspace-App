import './EmptyState.css'

/** mascotSlot lets the real mascot asset (designed separately) drop in
 * later without changing this component's contract. */
function EmptyState({ mascotSlot, onNewWorkspace }) {
  return (
    <div className="empty-state">
      <div className="empty-state__mascot">{mascotSlot ?? <DefaultMascot />}</div>
      <p className="empty-state__message">Wanna start something?</p>
      <button
        type="button"
        className="empty-state__cta"
        onClick={onNewWorkspace}
      >
        + New workspace
      </button>
    </div>
  )
}

/** Placeholder "ball with arms and legs" sketch, swappable via mascotSlot. */
function DefaultMascot() {
  return (
    <svg viewBox="0 0 100 100" width="96" height="96" aria-hidden="true">
      <circle cx="50" cy="42" r="22" fill="var(--color-brand-primary)" />
      <line
        x1="32"
        y1="55"
        x2="20"
        y2="70"
        stroke="var(--color-brand-primary)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="68"
        y1="55"
        x2="80"
        y2="70"
        stroke="var(--color-brand-primary)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="40"
        y1="62"
        x2="36"
        y2="80"
        stroke="var(--color-brand-primary)"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <line
        x1="60"
        y1="62"
        x2="64"
        y2="80"
        stroke="var(--color-brand-primary)"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default EmptyState
