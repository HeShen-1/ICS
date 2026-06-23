import { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { submitFeedback } from '../../api/feedback';

interface Props {
  messageId: number;
}

export function FeedbackBar({ messageId }: Props) {
  const [feedback, setFeedback] = useState<string | null>(null);

  const handle = async (rating: 'positive' | 'negative') => {
    if (feedback) return;
    setFeedback(rating);
    try {
      await submitFeedback(messageId, rating);
    } catch {
      setFeedback(null); // Revert optimistic update on failure
    }
  };

  return (
    <div className="flex items-center gap-1 mt-1 ml-1">
      <button
        onClick={() => handle('positive')}
        disabled={!!feedback}
        className={`p-1 rounded transition ${feedback === 'positive' ? 'text-green-600' : 'text-gray-300 hover:text-green-500'}`}
      >
        <ThumbsUp size={14} />
      </button>
      <button
        onClick={() => handle('negative')}
        disabled={!!feedback}
        className={`p-1 rounded transition ${feedback === 'negative' ? 'text-red-600' : 'text-gray-300 hover:text-red-500'}`}
      >
        <ThumbsDown size={14} />
      </button>
      {feedback && <span className="text-xs text-gray-400 ml-1">感谢反馈</span>}
    </div>
  );
}
