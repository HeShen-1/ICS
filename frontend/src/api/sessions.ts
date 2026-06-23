import { request } from './client';

export interface Session {
  id: number;
  title: string;
  status: string;
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
  created_at: string;
}

export interface Reference {
  doc_name: string;
  snippet: string;
  score: number;
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
