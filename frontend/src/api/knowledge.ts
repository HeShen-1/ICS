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

export async function listDocuments(): Promise<{ documents: Document[]; total: number }> {
  return request('/knowledge/list');
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
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
