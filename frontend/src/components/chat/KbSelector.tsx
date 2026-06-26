import { useEffect, useState } from 'react';
import { Layers } from 'lucide-react';
import { getKnowledgeBases, type KnowledgeBase } from '../../api/knowledge';
import { useChatStore } from '../../stores/chatStore';

export function KbSelector() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const selectedKbId = useChatStore((s) => s.selectedKbId);
  const setSelectedKbId = useChatStore((s) => s.setSelectedKbId);

  useEffect(() => {
    getKnowledgeBases()
      .then((res) => setKbs(res.knowledge_bases))
      .catch(() => setKbs([]));
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    setSelectedKbId(val === '' ? null : Number(val));
  };

  return (
    <div className="flex items-center gap-2 px-6 py-2 border-b border-gray-100 bg-white">
      <Layers size={16} className="text-indigo-500 shrink-0" />
      <select
        value={selectedKbId ?? ''}
        onChange={handleChange}
        className="flex-1 px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white text-gray-700 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition"
      >
        <option value="">自动路由</option>
        {kbs.map((kb) => (
          <option key={kb.id} value={kb.id}>
            {kb.name}
          </option>
        ))}
      </select>
    </div>
  );
}
