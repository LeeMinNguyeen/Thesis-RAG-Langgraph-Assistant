// ChatBubble component - Individual message bubble

import './ChatBubble.css';

// Import avatars
import userAvatar from '../assets/images/user.png';
import chatbotAvatar from '../assets/images/logouel25.jpg';

interface ChatBubbleProps {
  origin: 'human' | 'ai';
  message: string;
}

export function ChatBubble({ origin, message }: ChatBubbleProps) {
  const isAi = origin === 'ai';
  const avatar = isAi ? chatbotAvatar : userAvatar;

  return (
    <div className={`chat-row ${isAi ? 'ai' : 'user'}`}>
      {isAi && (
        <img
          className="chat-icon"
          src={avatar}
          alt="AI Avatar"
          width={32}
          height={32}
        />
      )}
      <div className={`chat-bubble ${isAi ? 'ai-bubble' : 'human-bubble'}`}>
        {message}
      </div>
      {!isAi && (
        <img
          className="chat-icon"
          src={avatar}
          alt="User Avatar"
          width={32}
          height={32}
        />
      )}
    </div>
  );
}
