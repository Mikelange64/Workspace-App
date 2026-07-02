import filobeloReading from '../../assets/mascott/filobelo_reading.svg'
import './EmptyState.css'

function EmptyState({ mascotSlot, onNewWorkspace }) {
  return (
    <div className="empty-state">
      <div className="empty-state__mascot">
        {mascotSlot ?? <img src={filobeloReading} alt="" className="empty-state__mascot-img" />}
      </div>
      <p className="empty-state__message">Nothing planned! Anything in mind?</p>
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

export default EmptyState
