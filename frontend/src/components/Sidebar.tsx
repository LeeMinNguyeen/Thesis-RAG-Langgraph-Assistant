// Sidebar component - Left column with logo, new chat button, and history

import type { ChatSession } from '../types';
import './Sidebar.css';

// Import logo image
import uelLogo from '../assets/images/logouel25y.png';

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId: string;
  onNewChat: () => void;
  onLoadSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
  isLoading: boolean;
}

export function Sidebar({
  sessions,
  currentSessionId,
  onNewChat,
  onLoadSession,
  onDeleteSession,
  isLoading
}: SidebarProps) {
  const truncateText = (text: string, maxLength: number = 40) => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <img src={uelLogo} alt="UEL Logo" className="sidebar-logo-img" />
      </div>

      <div className="sidebar-divider"></div>

      {/* New Chat Button */}
      <button
        className="new-chat-btn"
        onClick={onNewChat}
        disabled={isLoading}
      >
        Đoạn chat mới
      </button>

      <div className="sidebar-divider"></div>

      {/* History Section */}
      <h3 className="history-title">Lịch sử hội thoại</h3>

      <div className="history-container">
        {sessions.length > 0 ? (
          sessions.map((session) => (
            <div
              key={session.session_id}
              className={`history-item ${session.session_id === currentSessionId ? 'active' : ''}`}
            >
              <button
                className="history-item-btn"
                onClick={() => onLoadSession(session.session_id)}
                title={`${session.message_count} tin nhắn`}
              >
                {truncateText(session.first_message)}
              </button>
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteSession(session.session_id);
                }}
                title="Xóa"
              >
                🗑️
              </button>
            </div>
          ))
        ) : (
          <div className="no-history">
            Chưa có lịch sử hội thoại nào.
          </div>
        )}
      </div>
    </aside>
  );
}
