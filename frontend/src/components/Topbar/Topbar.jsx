import useDismissableMenu from '../../hooks/useDismissableMenu'
import ThemeToggle from '../shared/ThemeToggle'
import './Topbar.css'

function Topbar({
  logoSlot,
  searchValue = '',
  onSearchChange,
  onSearchSubmit,
  user = null,
  notificationCount = 0,
  onCalendarToggle,
  onNotificationsClick,
  onProfileClick,
}) {
  const [profileOpen, setProfileOpen, profileRef] = useDismissableMenu()

  function handleSubmit(event) {
    event.preventDefault()
    onSearchSubmit?.(searchValue)
  }

  function handleProfileItemClick(action) {
    setProfileOpen(false)
    onProfileClick?.(action)
  }

  return (
    <header className="topbar">
      <div className="topbar__logo">
        {logoSlot ?? <span className="topbar__logo-placeholder">WS</span>}
      </div>

      <form className="topbar__search" role="search" onSubmit={handleSubmit}>
        <label htmlFor="workspace-search" className="topbar__search-label">
          Search workspaces
        </label>
        <input
          id="workspace-search"
          type="search"
          className="topbar__search-input"
          placeholder="Search workspaces"
          value={searchValue}
          onChange={(event) => onSearchChange?.(event.target.value)}
        />
      </form>

      <div className="topbar__actions">
        <ThemeToggle />

        <button
          type="button"
          className="topbar__icon-btn topbar__icon-btn--muted"
          aria-label="Calendar (coming soon)"
          onClick={onCalendarToggle}
        >
          <CalendarIcon />
        </button>

        <button
          type="button"
          className="topbar__icon-btn topbar__icon-btn--muted"
          aria-label={
            notificationCount > 0
              ? `Notifications (${notificationCount} unread, coming soon)`
              : 'Notifications (coming soon)'
          }
          onClick={onNotificationsClick}
        >
          <BellIcon />
          {notificationCount > 0 && (
            <span className="topbar__badge">{notificationCount}</span>
          )}
        </button>

        <div className="topbar__profile" ref={profileRef}>
          <button
            type="button"
            className="topbar__avatar-btn"
            aria-label={user ? `Account: ${user.name}` : 'Account'}
            aria-haspopup="menu"
            aria-expanded={profileOpen}
            onClick={() => setProfileOpen((open) => !open)}
          >
            {user?.avatarUrl ? (
              <img
                src={user.avatarUrl}
                alt=""
                className="topbar__avatar-img"
              />
            ) : (
              <span className="topbar__avatar-placeholder">
                {user?.name ? user.name[0].toUpperCase() : '?'}
              </span>
            )}
          </button>

          {profileOpen && (
            <ul className="topbar__profile-menu" role="menu">
              <li role="none">
                <button
                  type="button"
                  role="menuitem"
                  className="topbar__profile-menu-item"
                  onClick={() => handleProfileItemClick('profile')}
                >
                  Profile
                </button>
              </li>
              <li role="none">
                <button
                  type="button"
                  role="menuitem"
                  className="topbar__profile-menu-item"
                  onClick={() => handleProfileItemClick('settings')}
                >
                  Settings
                </button>
              </li>
              <li role="none">
                <button
                  type="button"
                  role="menuitem"
                  className="topbar__profile-menu-item"
                  onClick={() => handleProfileItemClick('sign-out')}
                >
                  Sign out
                </button>
              </li>
            </ul>
          )}
        </div>
      </div>
    </header>
  )
}

function CalendarIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <rect
        x="3"
        y="5"
        width="18"
        height="16"
        rx="2"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" strokeWidth="1.6" />
      <line x1="8" y1="3" x2="8" y2="7" stroke="currentColor" strokeWidth="1.6" />
      <line x1="16" y1="3" x2="16" y2="7" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <path
        d="M6 17h12l-1.5-2.5V10a4.5 4.5 0 0 0-9 0v4.5L6 17Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M10 19a2 2 0 0 0 4 0"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

export default Topbar
