import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { listDocuments, uploadDocument, deleteDocument, type Document } from '../api/knowledge';
import { ArrowLeft, Upload, Trash2, Loader2, CheckCircle, XCircle } from 'lucide-react';

const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
  ready: { icon: CheckCircle, color: 'text-green-500', label: '就绪' },
  processing: { icon: Loader2, color: 'text-blue-500', label: '处理中' },
  failed: { icon: XCircle, color: 'text-red-500', label: '失败' },
};

const typeIcons: Record<string, string> = { txt: '📄', md: '📝', pdf: '📕' };

export function KnowledgePage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const fetchDocs = async () => {
    try {
      const res = await listDocuments();
      setDocs(res.documents);
    } catch {}
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await uploadDocument(file);
      await fetchDocs();
    } catch {}
    setUploading(false);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除此文档？向量数据将同步清除。')) return;
    try {
      await deleteDocument(id);
      await fetchDocs();
    } catch {}
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

        {/* Upload */}
        <div className="mb-6">
          <label className="flex items-center justify-center gap-2 px-6 py-10 border-2 border-dashed border-gray-300 rounded-xl cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition">
            <Upload size={20} className="text-gray-400" />
            <span className="text-sm text-gray-500">{uploading ? '上传中...' : '点击上传文档 (.txt / .md / .pdf，最大 10MB)'}</span>
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
                  <td colSpan={6} className="text-center py-12 text-gray-400 text-sm">暂无知识库文档</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
