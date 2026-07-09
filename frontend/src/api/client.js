const BASE_URL = import.meta.env.VITE_API_URL

const STORAGE_KEYS = {
  access: 'filobelo_access_token',
  refresh: 'filobelo_refresh_token',
}

export function getTokens() {
  return {
    access: localStorage.getItem(STORAGE_KEYS.access),
    refresh: localStorage.getItem(STORAGE_KEYS.refresh),
  }
}

export function setTokens(access, refresh) {
  localStorage.setItem(STORAGE_KEYS.access, access)
  localStorage.setItem(STORAGE_KEYS.refresh, refresh)
}

export function clearTokens() {
  localStorage.removeItem(STORAGE_KEYS.access)
  localStorage.removeItem(STORAGE_KEYS.refresh)
}

// Refresh tokens rotate on use (the server deletes the old one and issues a
// new one atomically), so concurrent callers must not each fire their own
// refresh - only the first would succeed and the rest would 401, clearing
// the session that first call just established. This makes every caller
// share a single in-flight refresh instead.
let refreshPromise = null

async function attemptRefresh() {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const { refresh } = getTokens()
    if (!refresh) throw new Error('No refresh token')

    const res = await fetch(`${BASE_URL}/users/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })

    if (!res.ok) {
      clearTokens()
      throw new Error('Refresh failed')
    }

    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return data.access_token
  })()

  try {
    return await refreshPromise
  } finally {
    refreshPromise = null
  }
}

// Authenticated fetch — adds Bearer header, retries once after a 401 via refresh.
// On a second 401 or refresh failure, clears tokens and redirects to /login.
export async function authFetch(path, options = {}) {
  const { access } = getTokens()

    const makeHeaders = (token) => ({
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
    })

  let res = await fetch(`${BASE_URL}${path}`, { ...options, headers: makeHeaders(access) })

  if (res.status === 401) {
    try {
      const newToken = await attemptRefresh()
      res = await fetch(`${BASE_URL}${path}`, { ...options, headers: makeHeaders(newToken) })
    } catch {
      clearTokens()
      window.dispatchEvent(new CustomEvent('auth:expired'))
      throw new ApiError(401, 'Session expired')
    }
  }

  return parseResponse(res)
}

async function parseResponse(res) {
  if (res.status === 204) return null
  if (res.ok) return res.json()

  let detail = 'Request failed'
  try {
    const body = await res.json()
    detail = body.message ?? body.detail ?? detail
  } catch { /* non-JSON error body */ }
  throw new ApiError(res.status, detail)
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

// Login uses OAuth2PasswordRequestForm — must send application/x-www-form-urlencoded.
// The `username` field accepts either email or username (see backend router).
export async function loginRequest(emailOrUsername, password) {
  const body = new URLSearchParams({ username: emailOrUsername, password })
  const res = await fetch(`${BASE_URL}/users/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  const data = await parseResponse(res)
  setTokens(data.access_token, data.refresh_token)
  return data
}

// Register — JSON body.
export async function registerRequest(username, email, password) {
  const res = await fetch(`${BASE_URL}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })
  return parseResponse(res)
}

// Logout — deletes server-side refresh token.
export function logoutRequest(refreshToken) {
  return authFetch('/users/logout', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

// Workspace mutations
export function createWorkspace(data) {
  return authFetch('/workspaces', { method: 'POST', body: JSON.stringify(data) })
}

export function patchWorkspace(id, data) {
  return authFetch(`/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteWorkspace(id) {
  return authFetch(`/workspaces/${id}/`, { method: 'DELETE' })
}

export function completeWorkspace(id) {
  return authFetch(`/workspaces/${id}/complete`, { method: 'PATCH' })
}

export function reopenWorkspace(id) {
  return authFetch(`/workspaces/${id}/reopen`, { method: 'PATCH' })
}

export function leaveWorkspace(id) {
  return authFetch(`/workspaces/${id}/members/me`, { method: 'DELETE' })
}

// Workspace lists
export function getCompletedWorkspaces(skip = 0, limit = 20) {
  return authFetch(`/workspaces/completed?skip=${skip}&limit=${limit}`)
}

// Workspace detail
export function getWorkspace(id) {
  return authFetch(`/workspaces/${id}`)
}

export function getMembersWithRoles(workspaceId) {
  return authFetch(`/workspaces/${workspaceId}/members`)
}

export function inviteMember(workspaceId, userId) {
  return authFetch(`/workspaces/${workspaceId}/members/${userId}`, { method: 'PATCH' })
}

export function inviteExternal(workspaceId, email) {
  return authFetch(`/workspaces/${workspaceId}/invite/external`, {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function promoteToAdmin(workspaceId, userId) {
  return authFetch(`/workspaces/${workspaceId}/members/${userId}/admin`, { method: 'PATCH' })
}

export function removeMember(workspaceId, userId) {
  return authFetch(`/workspaces/${workspaceId}/members/${userId}`, { method: 'DELETE' })
}

export function searchUser(q) {
  return authFetch(`/users/search?q=${encodeURIComponent(q)}`)
}

export function reassignTask(workspaceId, taskId, userId) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/owner?user_id=${userId}`, { method: 'PATCH' })
}

// Task CRUD (scoped to a workspace)
export function createTask(workspaceId, data) {
  return authFetch(`/workspaces/${workspaceId}/tasks/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function patchTask(workspaceId, taskId, data) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteTask(workspaceId, taskId) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}`, {
    method: 'DELETE',
  })
}

export function toggleTask(workspaceId, taskId) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/complete`, {
    method: 'PATCH',
  })
}

// Folders
export function getFolders() {
  return authFetch('/folders')
}

export function createFolder(name, color) {
  return authFetch('/folders', { method: 'POST', body: JSON.stringify({ name, color }) })
}

export function updateFolder(id, data) {
  return authFetch(`/folders/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteFolder(id) {
  return authFetch(`/folders/${id}`, { method: 'DELETE' })
}

// User self-management
export function updateUser(data) {
  return authFetch('/users/me', { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteAccount() {
  return authFetch('/users/me', { method: 'DELETE' })
}

export function changePassword(currentPassword, newPassword) {
  return authFetch('/users/me/password', {
    method: 'PATCH',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })
}

export function removeAvatar() {
  return authFetch('/users/me/picture', { method: 'DELETE' })
}

export async function verifyEmail(token) {
  const res = await fetch(`${BASE_URL}/users/verify-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  })
  return parseResponse(res)
}

export async function resendVerification(identifier) {
  const res = await fetch(`${BASE_URL}/users/resend-verification`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier }),
  })
  return parseResponse(res)
}

export async function forgotPassword(email) {
  const res = await fetch(`${BASE_URL}/users/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  return parseResponse(res)
}

export async function resetPassword(token, newPassword) {
  const res = await fetch(`${BASE_URL}/users/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword }),
  })
  return parseResponse(res)
}

// Avatar upload — multipart, so Content-Type must NOT be set manually
// (the browser sets it with the correct boundary).
export async function uploadAvatarRequest(file) {
  const { access } = getTokens()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/users/me/picture`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${access}` },
    body: form,
  })
  return parseResponse(res)
}

// Resources (scoped to a workspace + task)
export function listResources(workspaceId, taskId) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/resource/`)
}

export function createLink(workspaceId, taskId, data) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/resource/links`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function createNote(workspaceId, taskId, data) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/resource/notes`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function deleteResource(workspaceId, taskId, resourceId) {
  return authFetch(`/workspaces/${workspaceId}/tasks/${taskId}/resource/${resourceId}`, {
    method: 'DELETE',
  })
}

// File resource upload — multipart, same pattern as uploadAvatarRequest.
export async function uploadResourceFile(workspaceId, taskId, file) {
  const { access } = getTokens()
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/workspaces/${workspaceId}/tasks/${taskId}/resource/files`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${access}` },
    body: form,
  })
  return parseResponse(res)
}
