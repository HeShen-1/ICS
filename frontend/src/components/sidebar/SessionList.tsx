import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { listSessions, createSession } from '../../api/sessions';
import type { Session } from '../../api/sessions';
import { useSessionStore } from '../../stores/sessionStore';
import { MessageSquare, Plus, LogOut, Database } from 'lucide-react';
import { useAuthStore } from '../../stores/authStore';

export function SessionList() {
  const { sessions, setSessions } = useSessionStore();
  const navigate = useNavigate();
  const { sessionId } = useParams();
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    listSessions()
      .then((res) => setSessions(res.sessions))
      .catch(() => {});
  }, [setSessions]);

  const handleNew = async () => {
    try {
      const s = await createSession();
      setSessions([s, ...sessions]);
      navigate(`/chat/${s.id}`);
    } catch {}
  };

  return (
    <div className="w-64 h-screen bg-gray-900 text-gray-100 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <button
          onClick={handleNew}
          className="w-full flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition text-sm font-medium"
        >
          <Plus size={16} /> 新建会话
        </button>
      </div>

      <div className="flex-1 overflow-y-auto sidebar-scroll p-2 space-y-1">
        {sessions.map((s) => (
          <button
            key={s.id}
            onClick={() => navigate(`/chat/${s.id}`)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition flex items-center gap-2 ${
              String(s.id) === sessionId ? 'bg-gray-700 text-white' : 'hover:bg-gray-800 text-gray-300'
            }`}
          >
            <MessageSquare size={14} />
            <span className="truncate">{s.title || '新会话'}</span>
          </button>
        ))}
        {sessions.length === 0 && (
          <p className="text-gray-500 text-xs text-center py-8">暂无会话</p>
        )}
      </div>

      <div className="p-3 border-t border-gray-700 space-y-1">
        <button
          onClick={() => navigate('/knowledge')}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <Database size={14} /> 知识库管理
        </button>
        <button
          onClick={() => { logout(); navigate('/login'); }}
          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 rounded-lg transition"
        >
          <LogOut size={14} /> 退出登录
        </button>
      </div>
    </div>
  );
}
