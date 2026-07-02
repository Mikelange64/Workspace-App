import { useState, useEffect, useRef } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Topbar from './components/Topbar/Topbar'
import Sidebar from './components/Sidebar/Sidebar'
import NewWorkspaceModal from './components/Home/NewWorkspaceModal'
import ProfileModal from './components/Profile/ProfileModal'
import CalendarModal from './components/Calendar/CalendarModal'
import CompletedWorkspacesModal from './components/Home/CompletedWorkspacesModal'
import Toast from './components/shared/Toast'
import { useAuth } from './context/AuthContext'
import {
  authFetch,
  createWorkspace,
  patchWorkspace,
  deleteWorkspace,
  leaveWorkspace,
  getFolders,
  createFolder,
  updateFolder,
  deleteFolder,
  getCompletedWorkspaces,
  completeWorkspace,
  reopenWorkspace,
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
    folderId: ws.folder_id ?? null,
    members: ws.members?.map((m) => ({
      id: m.id,
      name: m.username,
      avatarUrl: toAvatarUrl(m.image_path),
    })),
    isCompleted: ws.is_completed ?? false,
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
  const location = useLocation()
  const [workspaces, setWorkspaces] = useState([])
  const [folders, setFolders] = useState([])
  const [searchValue, setSearchValue] = useState('')
  const [showNewModal, setShowNewModal] = useState(false)
  const [showProfileModal, setShowProfileModal] = useState(false)
  const [showCalendar, setShowCalendar] = useState(false)
  const [calendarPrefillDate, setCalendarPrefillDate] = useState(null)
  const [toast, setToast] = useState(null)
  const [showCompletedModal, setShowCompletedModal] = useState(false)
  const [completedTotal, setCompletedTotal] = useState(0)

  function showComingSoon() {
    setToast('Currently unavailable — coming soon')
  }

  async function loadData() {
    try {
      const [wsData, folderData, completedData] = await Promise.all([
        authFetch('/workspaces'),
        getFolders(),
        getCompletedWorkspaces(0, 1),
      ])
      setWorkspaces(wsData.workspaces.map(normalizeWorkspace))
      setFolders(folderData)
      setCompletedTotal(completedData.total)
    } catch {
      setToast('Failed to load workspaces — please refresh')
    }
  }

  // Initial load
  useEffect(() => {
    loadData()
  }, [])

  // Re-fetch whenever the user navigates back to home
  const isFirstRender = useRef(true)
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false
      return
    }
    if (location.pathname === '/') {
      loadData()
    }
  }, [location.pathname])

  const currentUser = {
    name: user?.username,
    avatarUrl: toAvatarUrl(user?.image_path),
  }

  const activeWorkspaces = workspaces.filter(
    (ws) => !ws.isArchived && !ws.isCompleted
  )

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
      setToast(err.message ?? 'Could not delete workspace')
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
      setToast(err.message ?? 'Could not leave workspace')
    }
  }

  async function handleMoveToFolder(workspaceId, folderId) {
    const ws = workspaces.find((w) => w.id === workspaceId)
    if (!ws) return
    setWorkspaces((prev) => prev.map((w) => w.id === workspaceId ? { ...w, folderId } : w))
    try {
      await patchWorkspace(workspaceId, { folder_id: folderId })
    } catch {
      setWorkspaces((prev) => prev.map((w) => w.id === workspaceId ? { ...w, folderId: ws.folderId } : w))
    }
  }

  async function handleCreateFolder(name, color) {
    const folder = await createFolder(name, color)
    setFolders((prev) => [...prev, folder])
  }

  async function handleUpdateFolder(id, data) {
    const updated = await updateFolder(id, data)
    setFolders((prev) => prev.map((f) => (f.id === id ? updated : f)))
  }

  async function handleDeleteFolder(id) {
    const folder = folders.find((f) => f.id === id)
    setFolders((prev) => prev.filter((f) => f.id !== id))
    setWorkspaces((prev) => prev.map((w) => w.folderId === id ? { ...w, folderId: null } : w))
    try {
      await deleteFolder(id)
    } catch {
      setFolders((prev) => [...prev, folder])
    }
  }

  async function handleWorkspaceCompleted(wsId) {
    await completeWorkspace(wsId)
    setWorkspaces((prev) => prev.filter((ws) => ws.id !== wsId))
    setCompletedTotal((c) => c + 1)
  }

  async function handleWorkspaceReopened(wsId) {
    await reopenWorkspace(wsId)
    setWorkspaces((prev) => prev.map((ws) => ws.id === wsId ? { ...ws, isCompleted: false } : ws))
    setCompletedTotal((c) => Math.max(0, c - 1))
  }

  function handleTaskToggled(wsId, taskId, isCompleted) {
    setWorkspaces((prev) =>
      prev.map((ws) => {
        if (ws.id !== wsId) return ws
        const tasks = ws.tasks.map((t) => (t.id === taskId ? { ...t, isCompleted } : t))
        const done = tasks.filter((t) => t.isCompleted).length
        const progress = tasks.length > 0 ? Math.round((done / tasks.length) * 100) : 0
        return { ...ws, tasks, progress }
      })
    )
  }

  function handleWorkspaceTasksChanged(wsId, tasks) {
    setWorkspaces((prev) =>
      prev.map((ws) => {
        if (ws.id !== wsId) return ws
        const done = tasks.filter((t) => t.isCompleted).length
        const progress = tasks.length > 0 ? Math.round((done / tasks.length) * 100) : 0
        return { ...ws, tasks, progress }
      })
    )
  }

  async function handleCreateWorkspace(data) {
    const ws = await createWorkspace(data)
    setWorkspaces((prev) => [normalizeWorkspace(ws), ...prev])
    setShowNewModal(false)
    setCalendarPrefillDate(null)
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
    onComingSoon: showComingSoon,
    onTaskToggled: handleTaskToggled,
    onWorkspaceTasksChanged: handleWorkspaceTasksChanged,
    onWorkspaceCompleted: handleWorkspaceCompleted,
    onWorkspaceReopened: handleWorkspaceReopened,
    onToast: setToast,
  }

  return (
    <div className="app-shell">
      <Sidebar
        workspaces={activeWorkspaces}
        completedCount={completedTotal}
        folders={folders}
        currentUser={currentUser}
        onNewWorkspace={() => setShowNewModal(true)}
        onOpenInbox={showComingSoon}
        onOpenCompleted={() => setShowCompletedModal(true)}
        onSelectWorkspace={handleSelectWorkspace}
        onTogglePin={handleTogglePin}
        onArchive={handleArchive}
        onLeave={handleLeave}
        onDelete={handleDelete}
        onCreateFolder={handleCreateFolder}
        onUpdateFolder={handleUpdateFolder}
        onDeleteFolder={handleDeleteFolder}
        onMoveToFolder={handleMoveToFolder}
        onProfileClick={() => setShowProfileModal(true)}
      />

      <div className="app-shell__main">
        <Topbar
          logoSlot={
            <button type="button" className="topbar__logo-btn" onClick={() => navigate('/')} aria-label="Go to home">
              <span className="topbar__logo-text">Filobelo</span>
            </button>
          }
          searchValue={searchValue}
          onSearchChange={setSearchValue}
          onSearchSubmit={() => {}}
          searchSuggestions={searchSuggestions}
          onSelectSuggestion={handleSelectWorkspace}
          user={currentUser}
          notificationCount={0}
          onCalendarToggle={() => setShowCalendar((v) => !v)}
          onNotificationsClick={showComingSoon}
          onProfileClick={(action) => {
            if (action === 'sign-out') logout()
            else if (action === 'account') setShowProfileModal(true)
          }}
        />
        <div className="app-shell__content">
          <Outlet context={outletCtx} />
        </div>
      </div>

      {showNewModal && (
        <NewWorkspaceModal
          onClose={() => { setShowNewModal(false); setCalendarPrefillDate(null) }}
          onCreate={handleCreateWorkspace}
          defaultDueDate={calendarPrefillDate}
        />
      )}

      {showCalendar && (
        <CalendarModal
          workspaces={activeWorkspaces}
          onClose={() => setShowCalendar(false)}
          onSelectWorkspace={(id) => { setShowCalendar(false); handleSelectWorkspace(id) }}
          onNewWorkspaceOnDate={(date) => {
            setCalendarPrefillDate(date)
            setShowNewModal(true)
          }}
        />
      )}

      {showProfileModal && (
        <ProfileModal onClose={() => setShowProfileModal(false)} onToast={setToast} />
      )}

      {showCompletedModal && (
        <CompletedWorkspacesModal
          onClose={() => setShowCompletedModal(false)}
          onSelectWorkspace={(id) => { setShowCompletedModal(false); handleSelectWorkspace(id) }}
        />
      )}

      {toast && <Toast message={toast} onDismiss={() => setToast(null)} />}
    </div>
  )
}

export default AppShell
