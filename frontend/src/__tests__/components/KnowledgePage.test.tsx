import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { KnowledgePage } from '../../pages/KnowledgePage';

// Mock the knowledge API
vi.mock('../../api/knowledge', () => ({
  getKnowledgeBases: vi.fn(),
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
  deleteDocument: vi.fn(),
  createKnowledgeBase: vi.fn(),
  deleteKnowledgeBase: vi.fn(),
}));

import * as knowledgeApi from '../../api/knowledge';

function renderPage() {
  return render(
    <MemoryRouter>
      <KnowledgePage />
    </MemoryRouter>,
  );
}

describe('KnowledgePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    vi.mocked(knowledgeApi.getKnowledgeBases).mockResolvedValue({
      knowledge_bases: [],
      total: 0,
    });
    vi.mocked(knowledgeApi.listDocuments).mockResolvedValue({
      documents: [],
      total: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('知识库管理')).toBeInTheDocument();
    });
  });

  it('renders KB list when loaded', async () => {
    vi.mocked(knowledgeApi.getKnowledgeBases).mockResolvedValue({
      knowledge_bases: [
        { id: 1, name: '产品手册', description: '产品相关文档', document_count: 3, created_at: '2025-01-01' },
        { id: 2, name: '技术文档', description: '技术相关', document_count: 5, created_at: '2025-01-02' },
      ],
      total: 2,
    });
    vi.mocked(knowledgeApi.listDocuments).mockResolvedValue({
      documents: [],
      total: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('产品手册')).toBeInTheDocument();
    });
    expect(screen.getByText('技术文档')).toBeInTheDocument();
  });

  it('shows the upload area', async () => {
    vi.mocked(knowledgeApi.getKnowledgeBases).mockResolvedValue({
      knowledge_bases: [],
      total: 0,
    });
    vi.mocked(knowledgeApi.listDocuments).mockResolvedValue({
      documents: [],
      total: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/上传文档/)).toBeInTheDocument();
    });
  });

  it('shows empty state when no documents', async () => {
    vi.mocked(knowledgeApi.getKnowledgeBases).mockResolvedValue({
      knowledge_bases: [],
      total: 0,
    });
    vi.mocked(knowledgeApi.listDocuments).mockResolvedValue({
      documents: [],
      total: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('暂无知识库文档')).toBeInTheDocument();
    });
  });
});
