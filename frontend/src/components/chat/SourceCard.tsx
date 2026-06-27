import { BookOpen } from 'lucide-react';

interface Props {
  docName: string;
  snippet: string;
  score: number;
  kbName?: string;
}

export function SourceCard({ docName, snippet, score, kbName }: Props) {
  return (
    <div className="flex items-start gap-2 px-2.5 py-1.5 bg-gray-50 rounded-lg text-xs text-gray-500">
      <BookOpen size={12} className="mt-0.5 shrink-0" />
      <div>
        <span className="font-medium text-gray-700">📚 参考：{docName}</span>
        {kbName && <span className="ml-1.5 text-indigo-500 bg-indigo-50 px-1 rounded">路由至「{kbName}」</span>}
        <span className="ml-2 text-gray-400">(相关度: {score})</span>
        {snippet && <p className="text-gray-400 mt-0.5 line-clamp-2">{snippet}</p>}
      </div>
    </div>
  );
}
