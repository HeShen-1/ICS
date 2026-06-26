import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listDocuments, uploadDocument, deleteDocument,
  getKnowledgeBases, createKnowledgeBase, deleteKnowledgeBase,
  type Document, type KnowledgeBase,
} from '../api/knowledge';
import { ArrowLeft, Upload, Trash2, Loader2, CheckCircle, XCircle, Plus, Layers, X } from 'lucide-react';

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
    setUploading(true);
    try {
      await uploadDocument(file, selectedKbId ?? undefined);
      await fetchDocs();
      await fetchKbs();
    } catch {
      setError('上传文档失败');
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
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

  const handleDeleteKb = async (id: number) => {
    if (!confirm('确认删除此知识库？知识库中的所有文档也将被删除。')) return;
    try {
      await deleteKnowledgeBase(id);
      if (selectedKbId === id) setSelectedKbId(null);
      await fetchKbs();
      await fetchDocs();
    } catch {
      setError('删除知识库失败');
    }
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
                  onClick={() => handleDeleteKb(kb.id)}
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
                      <button onClick={() => handleDelete(doc.id)} className="p-1.5 text-gray-400 hover:text-red-500 transition">
                        <Trash2 size={14} />
                      </button>
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
      </div>
    </div>
  );
}
