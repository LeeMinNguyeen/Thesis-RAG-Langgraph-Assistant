// ChatArea component - Main chat interface with messages and watermark

import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import { ChatBubble } from './ChatBubble';
import { ChatInput } from './ChatInput';
import './ChatArea.css';

// Import watermark
import watermarkLogo from '../assets/images/LogoAI4I-Xanh.png';

interface ChatAreaProps {
  messages: Message[];
  onSend: (message: string) => void;
  isSending: boolean;
}

export function ChatArea({ messages, onSend, isSending }: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <main className="chat-area">
      {/* Watermark */}
      <div className="watermark-container">
        <img src={watermarkLogo} alt="Watermark" className="watermark-img" />
      </div>

      {/* Messages Container */}
      <div className="messages-container">
        {messages.map((msg) => (
          <ChatBubble
            key={msg.id}
            origin={msg.origin}
            message={msg.message}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input */}
      <div className="input-container">
        <ChatInput onSend={onSend} isSending={isSending} />
      </div>
    </main>
  );
}
