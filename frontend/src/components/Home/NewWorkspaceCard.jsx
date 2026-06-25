import './NewWorkspaceCard.css'

function NewWorkspaceCard({ onClick }) {
  return (
    <button type="button" className="new-workspace-card" onClick={onClick}>
      <span className="new-workspace-card__plus" aria-hidden="true">
        +
      </span>
      <span>New workspace</span>
    </button>
  )
}

export default NewWorkspaceCard
