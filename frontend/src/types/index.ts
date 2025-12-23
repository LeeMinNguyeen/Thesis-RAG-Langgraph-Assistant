// Types for the chatbot application

export interface Message {
  id: string;
  origin: 'human' | 'ai';
  message: string;
  timestamp?: Date;
}

export interface ChatSession {
  session_id: string;
  first_message: string;
  message_count: number;
  created_at?: string;
  updated_at?: string;
}

export interface ChatResponse {
  response: string;
  history: Array<{
    user: string;
    bot: string;
  }>;
}

export interface SessionListResponse {
  total: number;
  sessions: ChatSession[];
}

export interface HistoryResponse {
  session_id: string;
  history: Array<{
    user: string;
    bot: string;
    timestamp?: string;
  }>;
}
