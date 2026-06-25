import { useState } from 'react'
import Topbar from './components/Topbar/Topbar'
import Sidebar from './components/Sidebar/Sidebar'
import HomeCanvas from './components/Home/HomeCanvas'
import './App.css'

const SAMPLE_WORKSPACES = [
  {
    id: 1,
    title: 'Portfolio launch',
    numOfTasks: 5,
    numOfMembers: 3,
    progress: 40,
    dueDate: '2026-07-01T00:00:00Z',
    isPinned: true,
    isArchived: false,
    dateCreated: '2026-06-01T00:00:00Z',
    currentUserRole: 'admin',
  },
  {
    id: 2,
    title: 'Overdue redesign',
    numOfTasks: 3,
    numOfMembers: 1,
    progress: 30,
    dueDate: '2026-06-01T00:00:00Z',
    isPinned: false,
    isArchived: false,
    dateCreated: '2026-06-10T00:00:00Z',
    currentUserRole: 'member',
  },
  {
    id: 3,
    title: 'Empty idea',
    numOfTasks: 0,
    numOfMembers: 1,
    progress: 0,
    dueDate: null,
    isPinned: false,
    isArchived: false,
    dateCreated: '2026-06-20T00:00:00Z',
    currentUserRole: 'admin',
  },
]

const SAMPLE_COMING_UP = [
  {
    id: 101,
    title: 'Finalize landing page copy',
    workspaceId: 1,
    workspaceTitle: 'Portfolio launch',
    workspaceStatus: 'in-progress',
    dueDate: '2026-06-26T00:00:00Z',
  },
  {
    id: 102,
    title: 'Fix broken nav links',
    workspaceId: 2,
    workspaceTitle: 'Overdue redesign',
    workspaceStatus: 'in-progress',
    dueDate: '2026-06-20T00:00:00Z',
  },
]

// const SAMPLE_WORKSPACES = [];
// const SAMPLE_COMING_UP = [];

function App() {
  const [searchValue, setSearchValue] = useState('')

  return (
    <div className="app-shell">
      <Sidebar
        workspaces={SAMPLE_WORKSPACES}
        currentUser={{ name: 'Mikelange', avatarUrl: null }}
        onNewWorkspace={() => console.log('new workspace')}
        onOpenInbox={() => console.log('open inbox')}
        onOpenKanbanOverview={() => console.log('open kanban overview')}
        onSelectWorkspace={(id) => console.log('select workspace', id)}
        onTogglePin={(id) => console.log('toggle pin', id)}
        onArchive={(id) => console.log('archive', id)}
        onDelete={(id) => console.log('delete', id)}
        onProfileClick={() => console.log('profile click')}
      />

      <div className="app-shell__main">
        <Topbar
          searchValue={searchValue}
          onSearchChange={setSearchValue}
          onSearchSubmit={(value) => console.log('search submit:', value)}
          user={{ name: 'Mikelange', avatarUrl: null }}
          notificationCount={2}
          onCalendarToggle={() => console.log('calendar toggle')}
          onNotificationsClick={() => console.log('notifications click')}
          onProfileClick={(action) => console.log('profile action:', action)}
        />

        <HomeCanvas
          workspaces={SAMPLE_WORKSPACES}
          comingUpTasks={SAMPLE_COMING_UP}
          onSelectWorkspace={(id) => console.log('open workspace', id)}
          onNewWorkspace={() => console.log('new workspace')}
          onSelectTask={(id) => console.log('open task', id)}
        />
      </div>
    </div>
  )
}

export default App
