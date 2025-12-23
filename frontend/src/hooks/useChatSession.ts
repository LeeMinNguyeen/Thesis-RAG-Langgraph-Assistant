// Custom hook for managing chat session state

import { useState, useCallback, useEffect, useRef } from 'react';
import type { Message, ChatSession } from '../types';
import {
  sendChatMessage,
  loadConversationFromApi,
  getAllSessions,
  deleteSession,
  createChatSession
} from '../services/api';

export function useChatSession() {
  const [sessionId, setSessionId] = useState<string>(() => {
    // Try to get from localStorage or generate new
    const stored = localStorage.getItem('chatbot_session_id');
    return stored || crypto.randomUUID();
  });
  
  const [history, setHistory] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use refs to always have access to current values in callbacks
  const sessionIdRef = useRef(sessionId);
  const historyRef = useRef(history);
  
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);
  
  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  // Save session ID to localStorage
  useEffect(() => {
    localStorage.setItem('chatbot_session_id', sessionId);
  }, [sessionId]);

  // Load session history
  const loadSessionHistory = useCallback(async (id: string, limit: number = 100) => {
    setIsLoading(true);
    setError(null);
    try {
      const messages = await loadConversationFromApi(id, limit);
      setHistory(messages);
      setSessionId(id);
    } catch (err) {
      setError('Failed to load conversation history');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load all sessions
  const loadAllSessions = useCallback(async (limit: number = 10) => {
    try {
      const allSessions = await getAllSessions(limit);
      setSessions(allSessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  }, []);

  // Send a message - not using useCallback to avoid closure issues
  const sendMessage = async (message: string) => {
    if (!message.trim() || isSending) return;
    
    setIsSending(true);
    setError(null);
    
    // Add user message immediately
    const userMessage: Message = {
      id: crypto.randomUUID(),
      origin: 'human',
      message: message
    };
    
    const newHistoryWithUser = [...historyRef.current, userMessage];
    setHistory(newHistoryWithUser);
    historyRef.current = newHistoryWithUser;
    
    try {
      const currentSessionId = sessionIdRef.current;
      console.log('Sending message to session:', currentSessionId);
      const result = await sendChatMessage(currentSessionId, message);
      console.log('Received result:', result);
      
      if (result && result.response) {
        const aiMessage: Message = {
          id: crypto.randomUUID(),
          origin: 'ai',
          message: result.response
        };
        
        const newHistoryWithAI = [...historyRef.current, aiMessage];
        console.log('Setting new history with AI message:', newHistoryWithAI);
        setHistory(newHistoryWithAI);
        historyRef.current = newHistoryWithAI;
        
        // Reload sessions to update the list
        loadAllSessions();
      } else {
        setError('Failed to get response from server');
      }
    } catch (err) {
      setError('Failed to send message');
      console.error(err);
    } finally {
      setIsSending(false);
    }
  };

  // Create new session
  const createNewSession = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const newSessionId = await createChatSession();
      if (newSessionId) {
        setSessionId(newSessionId);
        setHistory([]);
        await loadAllSessions();
        return true;
      }
      setError('Failed to create new session');
      return false;
    } catch (err) {
      setError('Failed to create new session');
      console.error(err);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [loadAllSessions]);

  // Delete a session
  const removeSession = useCallback(async (id: string) => {
    try {
      const success = await deleteSession(id);
      if (success) {
        // If deleting current session, create new one
        if (id === sessionId) {
          await createNewSession();
        } else {
          await loadAllSessions();
        }
        return true;
      }
      return false;
    } catch (err) {
      console.error('Failed to delete session:', err);
      return false;
    }
  }, [sessionId, createNewSession, loadAllSessions]);

  // Load a specific session
  const loadSession = useCallback(async (id: string) => {
    await loadSessionHistory(id);
  }, [loadSessionHistory]);

  // Initial load
  useEffect(() => {
    loadAllSessions();
    // Only load history if we have messages
    loadSessionHistory(sessionId);
  }, []);

  return {
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
    loadAllSessions,
    setError
  };
}
