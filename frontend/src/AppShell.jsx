import { useState, useEffect } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import Topbar from './components/Topbar/Topbar'
import Sidebar from './components/Sidebar/Sidebar'
import NewWorkspaceModal from './components/Home/NewWorkspaceModal'
import ProfileModal from './components/Profile/ProfileModal'
import { useAuth } from './context/AuthContext'
import {
  authFetch,
  createWorkspace,
  patchWorkspace,
  deleteWorkspace,
  leaveWorkspace,
} from './api/client'
import './App.css'

function toAvatarUrl(imagePath) {
  return imagePath?.startsWith('https://') ? imagePath : null
}

function normalizeWorkspace(ws) {
  return {
    id: ws.id,
    title: ws.title,
    description: ws.description,
    numOfTasks: ws.num_of_tasks,
    numOfMembers: ws.num_of_members,
    progress: ws.progress,
    dueDate: ws.due_date,
    isPinned: ws.is_pinned,
    isArchived: ws.is_archived,
    dateCreated: ws.date_created,
    maxNumber: ws.max_number,
    currentUserRole: ws.current_user_role ?? null,
    members: ws.members?.map((m) => ({
      id: m.id,
      name: m.username,
      avatarUrl: toAvatarUrl(m.image_path),
    })),
    tasks: ws.tasks?.map((t) => ({
      id: t.id,
      title: t.title,
      dueDate: t.due_date ?? null,
      isCompleted: t.is_completed,
    })) ?? [],
  }
}

function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [workspaces, setWorkspaces] = useState([])
  const [searchValue, setSearchValue] = useState('')
  const [showNewModal, setShowNewModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)

  useEffect(() => {
    async function loadWorkspaces() {
      try {
        const data = await authFetch('/workspaces')
        setWorkspaces(data.workspaces.map(normalizeWorkspace))
      } catch (err) {
        console.error(err)
      }
    }
    loadWorkspaces()
  }, [])

  const currentUser = {
    name: user?.username,
    avatarUrl: toAvatarUrl(user?.image_path),
  }

  const activeWorkspaces = workspaces.filter((ws) => !ws.isArchived)

  const searchSuggestions = searchValue.trim()
    ? activeWorkspaces.filter((ws) =>
        ws.title.toLowerCase().includes(searchValue.toLowerCase())
      )
    : []

  const upcomingTasks = activeWorkspaces.flatMap((ws) =>
    ws.tasks
      .filter((t) => !t.isCompleted)
      .map((t) => ({
        id: t.id,
        title: t.title,
        dueDate: t.dueDate,
        workspaceTitle: ws.title,
        workspaceId: ws.id,
      }))
  )

  function handleSelectWorkspace(id) {
    navigate(`/workspaces/${id}`)
  }

  async function handleTogglePin(id) {
    const ws = workspaces.find((w) => w.id === id)
    if (!ws) return
    const next = !ws.isPinned
    setWorkspaces((prev) =>
      prev.map((w) => (w.id === id ? { ...w, isPinned: next } : w))
    )
    try {
      await patchWorkspace(id, { is_pinned: next })
    } catch {
      setWorkspaces((prev) =>
        prev.map((w) => (w.id === id ? { ...w, isPinned: ws.isPinned } : w))
      )
    }
  }

  async function handleArchive(id) {
    const ws = workspaces.find((w) => w.id === id)
    if (!ws) return
    setWorkspaces((prev) =>
      prev.map((w) => (w.id === id ? { ...w, isArchived: true } : w))
    )
    try {
      await patchWorkspace(id, { is_archived: true })
    } catch {
      setWorkspaces((prev) =>
        prev.map((w) => (w.id === id ? { ...w, isArchived: false } : w))
      )
    }
  }

  async function handleDelete(id) {
    const ws = workspaces.find((w) => w.id === id)
    if (!ws) return
    setWorkspaces((prev) => prev.filter((w) => w.id !== id))
    try {
      await deleteWorkspace(id)
    } catch (err) {
      setWorkspaces((prev) => [ws, ...prev])
      alert(err.detail ?? 'Could not delete workspace') // TODO: replace with toast
    }
  }

  async function handleLeave(id) {
    const ws = workspaces.find((w) => w.id === id)
    if (!ws) return
    setWorkspaces((prev) => prev.filter((w) => w.id !== id))
    try {
      await leaveWorkspace(id)
    } catch (err) {
      setWorkspaces((prev) => [ws, ...prev])
      alert(err.detail ?? 'Could not leave workspace') // TODO: replace with toast
    }
  }

  async function handleCreateWorkspace(data) {
    const ws = await createWorkspace(data)
    setWorkspaces((prev) => [normalizeWorkspace(ws), ...prev])
    setShowNewModal(false)
  }

  const outletCtx = {
    workspaces,
    activeWorkspaces,
    upcomingTasks,
    onSelectWorkspace: handleSelectWorkspace,
    onNewWorkspace: () => setShowNewModal(true),
    onTogglePin: handleTogglePin,
    onArchive: handleArchive,
    onDelete: handleDelete,
    onLeave: handleLeave,
  }

  return (
    <div className="app-shell">
      <Sidebar
        workspaces={activeWorkspaces}
        currentUser={currentUser}
        onNewWorkspace={() => setShowNewModal(true)}
        onOpenInbox={() => console.log('open inbox')}
        onOpenKanbanOverview={() => console.log('open kanban overview')}
        onSelectWorkspace={handleSelectWorkspace}
        onTogglePin={handleTogglePin}
        onArchive={handleArchive}
        onLeave={handleLeave}
        onDelete={handleDelete}
        onProfileClick={() => setShowProfileModal(true)}
      />

      <div className="app-shell__main">
        <Topbar
          onLogoClick={() => navigate('/')}
          searchValue={searchValue}
          onSearchChange={setSearchValue}
          onSearchSubmit={(value) => console.log('search submit:', value)}
          searchSuggestions={searchSuggestions}
          onSelectSuggestion={handleSelectWorkspace}
          user={currentUser}
          notificationCount={0}
          onCalendarToggle={() => console.log('calendar toggle')}
          onNotificationsClick={() => console.log('notifications click')}
          onProfileClick={(action) => {
            if (action === 'sign-out') logout()
            else if (action === 'account') setShowProfileModal(true)
          }}
        />
        <Outlet context={outletCtx} />
      </div>

      {showNewModal && (
        <NewWorkspaceModal
          onClose={() => setShowNewModal(false)}
          onCreate={handleCreateWorkspace}
        />
      )}

      {showProfileModal && (
        <ProfileModal onClose={() => setShowProfileModal(false)} />
      )}
    </div>
  )
}

export default AppShell
