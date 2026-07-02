import WorkspaceGrid from './WorkspaceGrid'
import ComingUpSection from './ComingUpSection'
import './HomeCanvas.css'

function HomeCanvas({
  workspaces = [],
  membersByWorkspaceId,
  comingUpTasks = [],
  mascotSlot,
  onSelectWorkspace,
  onNewWorkspace,
  onComplete,
  onSelectTask,
}) {
  return (
    <div className="home-canvas">
      <WorkspaceGrid
        workspaces={workspaces}
        membersByWorkspaceId={membersByWorkspaceId}
        onSelectWorkspace={onSelectWorkspace}
        onNewWorkspace={onNewWorkspace}
        onComplete={onComplete}
        mascotSlot={mascotSlot}
      />
      <ComingUpSection
        tasks={comingUpTasks}
        onSelectTask={onSelectTask}
      />
    </div>
  )
}

export default HomeCanvas
