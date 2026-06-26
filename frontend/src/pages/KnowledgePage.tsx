import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listDocuments, uploadDocument, deleteDocument,
  getKnowledgeBases, createKnowledgeBase, deleteKnowledgeBase,
  getDocumentContent, getDocumentChunks,
  type Document, type KnowledgeBase,
  type DocumentContent, type DocumentChunks,
} from '../api/knowledge';
import { ArrowLeft, Upload, Trash2, Loader2, CheckCircle, XCircle, Plus, Layers, X, Eye, FileText, AlertCircle } from 'lucide-react';

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  ready: { icon: CheckCircle, color: 'text-green-500', label: '就绪' },
  processing: { icon: Loader2, color: 'text-indigo-500', label: '处理中' },
  failed: { icon: XCircle, color: 'text-red-500', label: '失败' },
};

const typeIcons: Record<string, string> = { txt: '📄', md: '📝', pdf: '📕' };

export function KnowledgePage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [selectedKbId, setSelectedKbId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [newKbDesc, setNewKbDesc] = useState('');
  const [creatingKb, setCreatingKb] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Issue 1: KB selection for upload
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [showKbSelect, setShowKbSelect] = useState(false);

  // Issue 2: View content & chunks
  const [viewingContent, setViewingContent] = useState(false);
  const [viewingChunks, setViewingChunks] = useState(false);
  const [contentData, setContentData] = useState<DocumentContent | null>(null);
  const [chunksData, setChunksData] = useState<DocumentChunks | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);

  // Issue 3: Delete KB confirmation
  const [deletingKb, setDeletingKb] = useState<KnowledgeBase | null>(null);

  const navigate = useNavigate();

  const fetchDocs = async () => {
    try {
      const res = await listDocuments(selectedKbId ?? undefined);
      setDocs(res.documents);
      setError(null);
    } catch {
      setError('加载文档列表失败');
    }
  };

  const fetchKbs = async () => {
    try {
      const res = await getKnowledgeBases();
      setKbs(res.knowledge_bases);
    } catch {
      // Silently fail for KB list
    }
  };

  useEffect(() => { fetchKbs(); }, []);
  useEffect(() => { fetchDocs(); }, [selectedKbId]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (selectedKbId === null) {
      if (kbs.length > 0) {
        setPendingFile(file);
        setShowKbSelect(true);
      } else {
        setError('请先创建一个知识库');
      }
      if (fileRef.current) fileRef.current.value = '';
      return;
    }
    setUploading(true);
    try {
      await uploadDocument(file, selectedKbId);
      await fetchDocs();
      await fetchKbs();
    } catch {
      setError('上传文档失败');
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleKbSelectUpload = async (kbId: number) => {
    if (!pendingFile) return;
    setShowKbSelect(false);
    setUploading(true);
    try {
      await uploadDocument(pendingFile, kbId);
      await fetchDocs();
      await fetchKbs();
    } catch {
      setError('上传文档失败');
    }
    setUploading(false);
    setPendingFile(null);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除此文档？向量数据将同步清除。')) return;
    try {
      await deleteDocument(id);
      await fetchDocs();
      await fetchKbs();
    } catch {
      setError('删除文档失败');
    }
  };

  const handleViewContent = async (docId: number) => {
    setLoadingContent(true);
    setViewingContent(true);
    try {
      const data = await getDocumentContent(docId);
      setContentData(data);
    } catch {
      setError('获取文档内容失败');
      setViewingContent(false);
    }
    setLoadingContent(false);
  };

  const handleViewChunks = async (docId: number) => {
    setLoadingChunks(true);
    setViewingChunks(true);
    try {
      const data = await getDocumentChunks(docId);
      setChunksData(data);
    } catch {
      setError('获取分块列表失败');
      setViewingChunks(false);
    }
    setLoadingChunks(false);
  };

  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName.trim()) return;
    setCreatingKb(true);
    try {
      await createKnowledgeBase({ name: newKbName.trim(), description: newKbDesc.trim() || undefined });
      await fetchKbs();
      setNewKbName('');
      setNewKbDesc('');
      setShowCreateKb(false);
    } catch {
      setError('创建知识库失败');
    }
    setCreatingKb(false);
  };

  const handleDeleteKb = (kb: KnowledgeBase) => {
    setDeletingKb(kb);
  };

  const confirmDeleteKb = async () => {
    if (!deletingKb) return;
    try {
      await deleteKnowledgeBase(deletingKb.id);
      if (selectedKbId === deletingKb.id) setSelectedKbId(null);
      await fetchKbs();
      await fetchDocs();
    } catch {
      setError('删除知识库失败');
    }
    setDeletingKb(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/chat')} className="p-2 hover:bg-gray-200 rounded-lg transition">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold">知识库管理</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600">
              <X size={14} />
            </button>
          </div>
        )}

        {/* KB Management Section */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-gray-600 flex items-center gap-1.5">
              <Layers size={16} className="text-indigo-500" />
              知识库
            </h2>
            <button
              onClick={() => setShowCreateKb(!showCreateKb)}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-indigo-600 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition"
            >
              <Plus size={14} />
              新建知识库
            </button>
          </div>

          {showCreateKb && (
            <form onSubmit={handleCreateKb} className="mb-3 p-4 bg-white border border-indigo-200 rounded-xl shadow-sm">
              <input
                type="text"
                placeholder="知识库名称"
                value={newKbName}
                onChange={(e) => setNewKbName(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg mb-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                required
              />
              <input
                type="text"
                placeholder="描述（可选）"
                value={newKbDesc}
                onChange={(e) => setNewKbDesc(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg mb-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
              />
              <div className="flex gap-2 justify-end">
                <button
                  type="button"
                  onClick={() => setShowCreateKb(false)}
                  className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 transition"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={creatingKb || !newKbName.trim()}
                  className="px-4 py-1.5 text-xs font-medium text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 disabled:opacity-40 transition"
                >
                  {creatingKb ? '创建中...' : '创建'}
                </button>
              </div>
            </form>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedKbId(null)}
              className={`px-3 py-1.5 text-xs rounded-lg border transition ${
                selectedKbId === null
                  ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-indigo-300 hover:text-indigo-600'
              }`}
            >
              全部文档
            </button>
            {kbs.map((kb) => (
              <div key={kb.id} className="flex items-center">
                <button
                  onClick={() => setSelectedKbId(kb.id)}
                  className={`px-3 py-1.5 text-xs rounded-l-lg border transition ${
                    selectedKbId === kb.id
                      ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-indigo-300 hover:text-indigo-600'
                  }`}
                  title={kb.description || kb.name}
                >
                  {kb.name}
                  <span className="ml-1 text-gray-400">({kb.document_count})</span>
                </button>
                <button
                  onClick={() => handleDeleteKb(kb)}
                  className="px-1.5 py-1.5 text-xs rounded-r-lg border border-l-0 border-gray-200 bg-white text-gray-400 hover:text-red-500 transition"
                  title="删除知识库"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Upload */}
        <div className="mb-6">
          <label className="flex items-center justify-center gap-2 px-6 py-10 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-indigo-400 hover:bg-blue-50/50 transition">
            <Upload size={20} className="text-gray-400" />
            <span className="text-sm text-gray-500">
              {uploading
                ? '上传中...'
                : selectedKbId !== null
                  ? `上传文档到所选知识库 (.txt / .md / .pdf，最大 10MB)`
                  : '点击上传文档 (.txt / .md / .pdf，最大 10MB)'}
            </span>
            <input ref={fileRef} type="file" accept=".txt,.md,.pdf" onChange={handleUpload} className="hidden" disabled={uploading} />
          </label>
        </div>

        {/* Doc List */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/50">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">文档名称</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">类型</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">状态</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">分块</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500">上传时间</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => {
                const status = statusConfig[doc.status] || statusConfig.failed;
                const StatusIcon = status.icon;
                return (
                  <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50/50 transition">
                    <td className="px-4 py-3 text-sm font-medium">{typeIcons[doc.file_type] || '📄'} {doc.name}</td>
                    <td className="px-4 py-3 text-xs text-gray-500 uppercase">{doc.file_type}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs ${status.color}`}>
                        <StatusIcon size={12} /> {status.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{doc.chunk_count} 块</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{new Date(doc.created_at).toLocaleDateString('zh-CN')}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-0.5">
                        <button
                          onClick={() => handleViewContent(doc.id)}
                          className="p-1.5 text-gray-400 hover:text-indigo-500 transition"
                          title="查看原文"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          onClick={() => handleViewChunks(doc.id)}
                          className="p-1.5 text-gray-400 hover:text-indigo-500 transition"
                          title="查看分块"
                        >
                          <FileText size={14} />
                        </button>
                        <button onClick={() => handleDelete(doc.id)} className="p-1.5 text-gray-400 hover:text-red-500 transition">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {docs.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400 text-sm">
                    {selectedKbId !== null ? '此知识库暂无文档' : '暂无知识库文档'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* KB Selection Modal (for upload when no KB selected) */}
        {showKbSelect && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setShowKbSelect(false); setPendingFile(null); }}>
            <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-6" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-sm font-semibold text-gray-800 mb-4">选择目标知识库</h3>
              {kbs.length === 0 ? (
                <div className="text-center py-4">
                  <AlertCircle size={40} className="mx-auto mb-3 text-amber-500" />
                  <p className="text-sm text-gray-600 mb-4">请先创建一个知识库</p>
                  <button
                    onClick={() => { setShowKbSelect(false); setPendingFile(null); setShowCreateKb(true); }}
                    className="px-4 py-2 text-sm font-medium text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 transition"
                  >
                    新建知识库
                  </button>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {kbs.map((kb) => (
                    <button
                      key={kb.id}
                      onClick={() => handleKbSelectUpload(kb.id)}
                      className="w-full text-left px-4 py-3 rounded-lg border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition"
                    >
                      <div className="text-sm font-medium text-gray-700">{kb.name}</div>
                      {kb.description && <div className="text-xs text-gray-400 mt-0.5">{kb.description}</div>}
                      <div className="text-xs text-gray-400 mt-0.5">{kb.document_count} 篇文档</div>
                    </button>
                  ))}
                </div>
              )}
              <div className="mt-4 flex justify-end">
                <button
                  onClick={() => { setShowKbSelect(false); setPendingFile(null); }}
                  className="px-3 py-1.5 text-xs text-gray-500 hover:text-gray-700 transition"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Document Content Modal */}
        {viewingContent && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setViewingContent(false); setContentData(null); }}>
            <div className="bg-white rounded-xl shadow-lg w-full max-w-2xl max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between p-4 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-800">查看原文 — {contentData?.name || ''}</h3>
                <button
                  onClick={() => { setViewingContent(false); setContentData(null); }}
                  className="p-1.5 text-gray-400 hover:text-gray-600 transition"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                {loadingContent ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 size={24} className="text-indigo-500 animate-spin" />
                  </div>
                ) : (
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">{contentData?.content || ''}</pre>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Document Chunks Modal */}
        {viewingChunks && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => { setViewingChunks(false); setChunksData(null); }}>
            <div className="bg-white rounded-xl shadow-lg w-full max-w-2xl max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between p-4 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-800">分块列表 — {chunksData?.name || ''}（{chunksData?.chunks.length || 0} 块）</h3>
                <button
                  onClick={() => { setViewingChunks(false); setChunksData(null); }}
                  className="p-1.5 text-gray-400 hover:text-gray-600 transition"
                >
                  <X size={16} />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                {loadingChunks ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 size={24} className="text-indigo-500 animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-3">
                    {chunksData?.chunks.map((chunk) => (
                      <div key={chunk.chunk_index} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                        <div className="text-xs text-indigo-500 font-medium mb-1">分块 #{chunk.chunk_index}</div>
                        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">{chunk.text}</pre>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Delete KB Confirmation Modal */}
        {deletingKb && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setDeletingKb(null)}>
            <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-6" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 bg-red-50 rounded-full">
                  <AlertCircle size={20} className="text-red-500" />
                </div>
                <h3 className="text-sm font-semibold text-gray-800">确认删除知识库</h3>
              </div>
              <p className="text-sm text-gray-600 mb-6">
                删除知识库「{deletingKb.name}」将同时删除其中的所有文档和向量数据，此操作不可撤销。
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setDeletingKb(null)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition"
                >
                  取消
                </button>
                <button
                  onClick={confirmDeleteKb}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-500 rounded-lg hover:bg-red-600 transition"
                >
                  确认删除
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
