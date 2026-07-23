import { useState } from 'react'
import MemberAvatar from './MemberAvatar'
import { SparkleIcon } from './icons'

export default function MessageBubble({ message, member, isSelf, isTyping = false, hideAvatar = false, isBot = false }) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const time = new Date(message.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  const sources = message.sources ?? []

  return (
    <div className={`message-row${isSelf ? ' message-row--self' : ''}`}>
      {!hideAvatar && (
        isBot
          ? <span className="message-row__bot-avatar" aria-label="Filobelo"><SparkleIcon size={14} /></span>
          : <MemberAvatar member={member} size={28} />
      )}
      <div className="message-row__body">
        {!isSelf && !hideAvatar && <span className="message-row__name">{member.name}</span>}
        <div className={`message-bubble${isSelf ? ' message-bubble--self' : ''}${isBot ? ' message-bubble--bot' : ''}${isTyping ? ' message-bubble--typing' : ''}`}>
          {message.content}
        </div>
        {sources.length > 0 && (
          <div className="message-row__sources">
            <button
              type="button"
              className="message-row__sources-toggle"
              onClick={() => setSourcesOpen((v) => !v)}
              aria-expanded={sourcesOpen}
            >
              🔎 {sources.length} source{sources.length === 1 ? '' : 's'}
              <span className="message-row__sources-chevron">{sourcesOpen ? '▴' : '▾'}</span>
            </button>
            {sourcesOpen && (
              <ul className="message-row__sources-list">
                {sources.map((s) => (
                  <li key={s.url}>
                    <a href={s.url} target="_blank" rel="noopener noreferrer">{s.title || s.url}</a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {!isTyping && <span className="message-row__time">{time}</span>}
      </div>
    </div>
  )
}
