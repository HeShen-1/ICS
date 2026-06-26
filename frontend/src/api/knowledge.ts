import { request } from './client';

export interface Document {
  id: number;
  name: string;
  file_type: string;
  status: string;
  chunk_count: number;
  file_size: number;
  created_at: string;
}

export interface KnowledgeBase {
  id: number;
  name: string;
  description: string;
  document_count: number;
  created_at: string;
}

export interface KnowledgeBaseCreate {
  name: string;
  description?: string;
}

export async function listDocuments(kbId?: number): Promise<{ documents: Document[]; total: number }> {
  const query = kbId !== undefined ? `?kb_id=${kbId}` : '';
  return request(`/knowledge/list${query}`);
}

export async function uploadDocument(file: File, kbId?: number): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  if (kbId !== undefined) {
    formData.append('kb_id', String(kbId));
  }
  const token = localStorage.getItem('token');
  const res = await fetch('/api/knowledge/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '上传失败' }));
    throw new Error(err.detail);
  }
  return res.json();
}

export async function deleteDocument(id: number): Promise<void> {
  return request(`/knowledge/${id}`, { method: 'DELETE' });
}

export async function getKnowledgeBases(): Promise<{ knowledge_bases: KnowledgeBase[]; total: number }> {
  return request('/knowledge/bases');
}

export async function createKnowledgeBase(data: KnowledgeBaseCreate): Promise<KnowledgeBase> {
  return request('/knowledge/bases', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateKnowledgeBase(id: number, data: Partial<KnowledgeBaseCreate>): Promise<KnowledgeBase> {
  return request(`/knowledge/bases/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteKnowledgeBase(id: number): Promise<void> {
  return request(`/knowledge/bases/${id}`, { method: 'DELETE' });
}
