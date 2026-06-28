import { useOutletContext } from 'react-router-dom'
import HomeCanvas from '../../components/Home/HomeCanvas'

function HomeView() {
  const { activeWorkspaces, upcomingTasks, onSelectWorkspace, onNewWorkspace } = useOutletContext()
  return (
    <HomeCanvas
      workspaces={activeWorkspaces}
      comingUpTasks={upcomingTasks}
      onSelectWorkspace={onSelectWorkspace}
      onNewWorkspace={onNewWorkspace}
      onSelectTask={(id) => console.log('open task', id)}
    />
  )
}

export default HomeView
