// Main App Component - Chatbot Application

import { useState, useEffect } from 'react';
import { Sidebar, ChatArea, Toast } from './components';
import { useChatSession } from './hooks/useChatSession';
import './App.css';

function App() {
  const {
    sessionId,
    history,
    sessions,
    isLoading,
    isSending,
    error,
    sendMessage,
    createNewSession,
    removeSession,
    loadSession,
    setError
  } = useChatSession();

  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Handle error with useEffect to avoid setting state during render
  useEffect(() => {
    if (error) {
      setToast({ message: error, type: 'error' });
      setError(null);
    }
  }, [error, setError]);

  const handleNewChat = async () => {
    const success = await createNewSession();
    if (success) {
      setToast({ message: 'Đã tạo session', type: 'success' });
    } else {
      setToast({ message: 'Không thể tạo đoạn chat mới', type: 'error' });
    }
  };

  const handleDeleteSession = async (id: string) => {
    const success = await removeSession(id);
    if (success) {
      setToast({ message: 'Đã xóa!', type: 'success' });
    } else {
      setToast({ message: 'Xóa thất bại!', type: 'error' });
    }
  };

  const handleLoadSession = async (id: string) => {
    await loadSession(id);
  };

  const handleSendMessage = (message: string) => {
    sendMessage(message);
  };

  // Debug: log history changes
  useEffect(() => {
    console.log('History updated:', history.length, 'messages');
  }, [history]);

  return (
    <div className="app-container">
      <Sidebar
        sessions={sessions}
        currentSessionId={sessionId}
        onNewChat={handleNewChat}
        onLoadSession={handleLoadSession}
        onDeleteSession={handleDeleteSession}
        isLoading={isLoading}
      />
      <ChatArea
        messages={history}
        onSend={handleSendMessage}
        isSending={isSending}
      />
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;
