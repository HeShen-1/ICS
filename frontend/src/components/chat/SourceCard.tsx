import { BookOpen } from 'lucide-react';

interface Props {
  docName: string;
  snippet: string;
  score: number;
}

export function SourceCard({ docName, snippet, score }: Props) {
  return (
    <div className="flex items-start gap-2 px-2.5 py-1.5 bg-gray-50 rounded-lg text-xs text-gray-500">
      <BookOpen size={12} className="mt-0.5 shrink-0" />
      <div>
        <span className="font-medium text-gray-700">📚 参考：{docName}</span>
        <span className="ml-2 text-gray-400">(相关度: {score})</span>
        {snippet && <p className="text-gray-400 mt-0.5 line-clamp-2">{snippet}</p>}
      </div>
    </div>
  );
}
