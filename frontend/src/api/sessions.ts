import { request } from './client';

export interface Session {
  id: number;
  title: string;
  status: string;
  pinned: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface SessionDetail extends Session {
  messages: Message[];
}

export interface Message {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  intent_tag: string | null;
  references: Reference[] | null;
  feedback_rating: string | null;  // "positive" | "negative" | null
  created_at: string;
}

export interface Reference {
  doc_name: string;
  snippet: string;
  score: number;
  kb_name?: string;
}

export async function listSessions(): Promise<{ sessions: Session[]; total: number }> {
  return request('/sessions');
}

export async function createSession(title?: string): Promise<Session> {
  return request('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: title || '新会话' }),
  });
}

export async function getSession(id: number): Promise<SessionDetail> {
  return request(`/sessions/${id}`);
}

export async function renameSession(id: number, title: string): Promise<Session> {
  return request(`/sessions/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ title }),
  });
}

export async function pinSession(id: number, pinned: boolean): Promise<Session> {
  return request(`/sessions/${id}/pin`, {
    method: 'PATCH',
    body: JSON.stringify({ pinned }),
  });
}

export async function deleteSession(id: number): Promise<void> {
  return request(`/sessions/${id}`, { method: 'DELETE' });
}
