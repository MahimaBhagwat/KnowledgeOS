export type ChatMessageRole = 'user' | 'assistant' | 'system';

export interface Citation {
  chunk_id: string;
  document_id: string;
  chunk_index: number;
  similarity_score: number;
  chunk_text: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: ChatMessageRole;
  content: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  citations: Citation[] | null;
  created_at: string;
}

export interface ChatSession {
  id: string;
  profile_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}
