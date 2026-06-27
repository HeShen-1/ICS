import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { listSessions, createSession, renameSession, pinSession, deleteSession } from '../../api/sessions';
import { useSessionStore } from '../../stores/sessionStore';
import { MessageSquare, Plus, LogOut, Database, BarChart3, Bot, MoreHorizontal, Pin, Pencil, Trash2 } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';
import { ConfirmModal } from '../ui/ConfirmModal';

export function SessionList() {
  const { sessions, setSessions, updateSession, removeSession } = useSessionStore();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const logout = useAuthStore((s) => s.logout);
  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState<number | null>(null);
  const [renaming, setRenaming] = useState<number | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; title: string } | null>(null);
  const [renameTitle, setRenameTitle] = useState('');

  useEffect(() => {
    listSessions()
      .then((res) => setSessions(res.sessions))
      .catch(() => setError('加载会话列表失败'));
  }, [setSessions]);

  // 点击外部关闭菜单
  useEffect(() => {
    if (menuOpen === null) return;
    const handler = () => setMenuOpen(null);
    window.addEventListener('click', handler);
    return () => window.removeEventListener('click', handler);
  }, [menuOpen]);

  const handleNew = async () => {
    try {
      const s = await createSession();
      setSessions([s, ...sessions]);
      navigate(`/chat/${s.id}`);
    } catch {}
  };

  const handleRename = async (id: number) => {
    if (!renameTitle.trim()) return;
    try {
      const s = await renameSession(id, renameTitle.trim());
      updateSession(id, { title: s.title });
    } catch {}
    setRenaming(null);
    setMenuOpen(null);
  };

  const handlePin = async (id: number, pinned: boolean) => {
    try {
      const s = await pinSession(id, pinned);
      updateSession(id, { pinned: s.pinned });
      // 重新拉取以重排序
      const res = await listSessions();
      setSessions(res.sessions);
    } catch {}
    setMenuOpen(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteSession(deleteTarget.id);
      removeSession(deleteTarget.id);
      if (String(deleteTarget.id) === sessionId) navigate('/chat');
    } catch {}
    setDeleteTarget(null);
    setMenuOpen(null);
  };

  return (
    <div className="w-64 h-screen bg-gray-900 text-gray-100 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={handleNew}
          className="w-full flex items-center gap-2 px-3 py-2 bg-indigo-500 hover:bg-indigo-600 rounded-lg transition text-sm font-medium"
        >
          <Plus size={16} /> 新建会话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto sidebar-scroll p-2 space-y-1">
        {error && (
          <p className="text-red-400 text-xs text-center py-4">{error}</p>
        )}
        {!error && sessions.length === 0 && (
          <p className="text-gray-500 text-xs text-center py-8">暂无会话</p>
        )}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group relative w-full text-left px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 cursor-pointer ${
              String(s.id) === sessionId ? 'bg-gray-700 text-white' : 'hover:bg-gray-800 text-gray-300'
            }`}
            onClick={() => navigate(`/chat/${s.id}`)}
          >
            <MessageSquare size={14} className="shrink-0" />
            {renaming === s.id ? (
              <input
                className="flex-1 bg-gray-600 text-white text-xs px-1 py-0.5 rounded outline-none border border-indigo-400"
                value={renameTitle}
                onChange={(e) => setRenameTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleRename(s.id);
                  if (e.key === 'Escape') { setRenaming(null); setMenuOpen(null); }
                }}
                onClick={(e) => e.stopPropagation()}
                autoFocus
              />
            ) : (
              <>
                <span className="truncate flex-1">
                  {s.pinned && <Pin size={10} className="inline mr-1 text-amber-400" />}
                  {s.title || '新会话'}
                </span>
                <button
                  className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-gray-600 transition"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMenuOpen(menuOpen === s.id ? null : s.id);
                  }}
                >
                  <MoreHorizontal size={14} />
                </button>
              </>
            )}

            {/* 下拉菜单 */}
            {menuOpen === s.id && (
              <div
                className="absolute right-0 top-full mt-1 z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-1 min-w-[120px]"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                  onClick={() => handlePin(s.id, !s.pinned)}
                >
                  <Pin size={12} /> {s.pinned ? '取消置顶' : '置顶'}
                </button>
                <button
                  className="w-full text-left px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 flex items-center gap-2"
                  onClick={() => {
                    setRenaming(s.id);
                    setRenameTitle(s.title);
                  }}
                >
                  <Pencil size={12} /> 重命名
                </button>
                <button
                  className="w-full text-left px-3 py-1.5 text-xs text-red-400 hover:bg-gray-700 flex items-center gap-2"
                  onClick={() => setDeleteTarget({ id: s.id, title: s.title })}
                >
                  <Trash2 size={12} /> 删除
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-gray-700 space-y-1">
        <button
          onClick={() => navigate('/knowledge')}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <Database size={14} /> 知识库管理
        </button>
        <button
          onClick={() => navigate('/stats')}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <BarChart3 size={14} /> 管理后台
        </button>
        <button
          onClick={() => navigate('/agent')}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <Bot size={14} /> Agent 拆解
        </button>
        <button
          onClick={() => { logout(); navigate('/login'); }}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <LogOut size={14} /> 退出登录
        </button>
      </div>

      <ConfirmModal
        open={deleteTarget !== null}
        title="删除会话"
        message={`确认删除「${deleteTarget?.title || ''}」？消息和反馈数据将一并清除，不可撤销。`}
        confirmLabel="确认删除"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
