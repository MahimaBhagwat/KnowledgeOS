import { apiDelete, apiGet, apiPatch, apiPost, supabase } from './api';
import type { ChatMessage, ChatSession } from '../types/chat';

export const chatSessionsQueryKey = ['chat-sessions'] as const;
export const chatSessionQueryKey = (sessionId: string) => ['chat-session', sessionId] as const;

export async function createSession(title?: string): Promise<ChatSession> {
  // Always send a valid JSON body to avoid backend 422 when title is missing
  return apiPost<ChatSession>('/chat/sessions', { title: title ?? 'New Chat' });
}

export async function listSessions(skip = 0, limit = 50): Promise<ChatSession[]> {
  return apiGet<ChatSession[]>('/chat/sessions', { skip, limit });
}

export async function getSession(sessionId: string): Promise<ChatSession> {
  return apiGet<ChatSession>(`/chat/sessions/${sessionId}`);
}

export async function renameSession(sessionId: string, title: string): Promise<ChatSession> {
  return apiPatch<ChatSession>(`/chat/sessions/${sessionId}`, { title });
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiDelete<void>(`/chat/sessions/${sessionId}`);
}

export async function sendMessage(
  sessionId: string,
  content: string,
  options?: { folderId?: string; topK?: number },
): Promise<ChatMessage> {
  return apiPost<ChatMessage>(`/chat/sessions/${sessionId}/messages`, {
    content,
    folder_id: options?.folderId,
    top_k: options?.topK ?? 5,
  });
}

export async function streamMessage(
  sessionId: string,
  payload: { content: string; folder_id?: string; top_k?: number },
  onToken: (text: string) => void,
): Promise<{ messageId: string; citations: any[] | null; promptTokens: number | null; completionTokens: number | null }> {
  // Reuse Supabase session retrieval from api.ts
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token ?? null;
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
  const url = `${baseUrl}/chat/sessions/${sessionId}/messages/stream`;

  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Streaming request failed: ${res.status} ${text}`);
  }

  if (!res.body) throw new Error('No response body for streaming request');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  return await new Promise(async (resolve, reject) => {
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Process complete SSE messages separated by double newline
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          // Each raw may contain multiple lines; look for lines starting with 'data:'
          const lines = raw.split(/\r?\n/);
          for (const line of lines) {
            if (!line.trim()) continue;
            if (line.startsWith('data:')) {
              const jsonPart = line.slice(5).trim();
              let payloadObj: any;
              try {
                payloadObj = JSON.parse(jsonPart);
              } catch (err) {
                // Malformed JSON from server — reject
                reject(new Error(`Malformed JSON in SSE data: ${jsonPart}`));
                return;
              }

              const t = payloadObj.type;
              if (t === 'token') {
                try {
                  onToken(String(payloadObj.content));
                } catch (e) {
                  // swallow onToken errors
                }
              } else if (t === 'done') {
                resolve({ messageId: payloadObj.message_id, citations: payloadObj.citations ?? null, promptTokens: payloadObj.prompt_tokens ?? null, completionTokens: payloadObj.completion_tokens ?? null });
                return;
              } else if (t === 'error') {
                const errDetail = payloadObj.detail ?? 'Stream error';
                const partial = payloadObj.partial_message_id ?? null;
                reject(new Error(`Stream error: ${errDetail} (partial=${partial})`));
                return;
              }
            }
          }
        }
      }

      // stream ended without a done event — try to flush remaining buffer
      if (buffer.trim()) {
        // process remaining lines
        const lines = buffer.split(/\r?\n/);
        for (const line of lines) {
          if (!line.trim()) continue;
          if (line.startsWith('data:')) {
            const jsonPart = line.slice(5).trim();
            try {
              const payloadObj = JSON.parse(jsonPart);
              if (payloadObj.type === 'done') {
                resolve({ messageId: payloadObj.message_id, citations: payloadObj.citations ?? null, promptTokens: payloadObj.prompt_tokens ?? null, completionTokens: payloadObj.completion_tokens ?? null });
                return;
              }
              if (payloadObj.type === 'error') {
                const errDetail = payloadObj.detail ?? 'Stream error';
                const partial = payloadObj.partial_message_id ?? null;
                reject(new Error(`Stream error: ${errDetail} (partial=${partial})`));
                return;
              }
            } catch (err) {
              // ignore
            }
          }
        }
      }

      reject(new Error('Stream ended without done event'));
    } catch (outerErr) {
      reject(outerErr);
    }
  });
}
