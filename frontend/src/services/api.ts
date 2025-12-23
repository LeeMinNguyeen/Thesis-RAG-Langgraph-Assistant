// API service for chatbot backend communication

import type { ChatResponse, ChatSession, HistoryResponse, Message } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Send a chat message to the API and get response.
 */
export async function sendChatMessage(sessionId: string, message: string): Promise<ChatResponse | null> {
  try {
    const params = new URLSearchParams({
      session_id: sessionId,
      message: message
    });
    
    const response = await fetch(`${API_BASE_URL}/chat?${params}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    // Backend returns "answer" but we normalize to "response" for frontend
    return {
      response: data.answer,
      history: data.history
    };
  } catch (error) {
    console.error('Failed to send message to API:', error);
    return null;
  }
}

/**
 * Load conversation history from API for a specific session.
 */
export async function loadConversationFromApi(sessionId: string, limit: number = 100): Promise<Message[]> {
  try {
    const params = new URLSearchParams({
      limit: limit.toString()
    });
    
    const response = await fetch(`${API_BASE_URL}/chat/history/${sessionId}?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data: HistoryResponse = await response.json();
    
    // Convert API response format to messages format
    const messages: Message[] = [];
    for (const item of data.history || []) {
      messages.push({
        id: crypto.randomUUID(),
        origin: 'human',
        message: item.user
      });
      messages.push({
        id: crypto.randomUUID(),
        origin: 'ai',
        message: item.bot
      });
    }
    
    return messages;
  } catch (error) {
    console.error('Failed to load conversation from API:', error);
    return [];
  }
}

/**
 * Get all chat sessions from API.
 */
export async function getAllSessions(limit: number = 10): Promise<ChatSession[]> {
  try {
    const params = new URLSearchParams({
      limit: limit.toString()
    });
    
    const response = await fetch(`${API_BASE_URL}/chat/sessions?${params}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.sessions || [];
  } catch (error) {
    console.error('Failed to load sessions from API:', error);
    return [];
  }
}

/**
 * Delete a session via API.
 */
export async function deleteSession(sessionId: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/session/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data.success || false;
  } catch (error) {
    console.error('Failed to delete session:', error);
    return false;
  }
}

/**
 * Create a new chat session via API.
 */
export async function createChatSession(): Promise<string | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/session/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (data.success) {
      return data.session_id;
    }
    return null;
  } catch (error) {
    console.error('Failed to create chat session:', error);
    return null;
  }
}
