import { useState } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
  maxLength?: number;
}

export function ChatInput({ onSend, disabled, maxLength = 500 }: Props) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    if (input.length > maxLength) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-gray-100 bg-white">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <div className="flex-1 relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题... (Enter 发送, Shift+Enter 换行)"
            className="w-full px-4 py-2.5 border border-gray-200 rounded-xl resize-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition text-sm"
            rows={2}
            disabled={disabled}
          />
          <span className={`absolute bottom-2 right-3 text-xs ${input.length > maxLength ? 'text-red-500' : 'text-gray-400'}`}>
            {input.length}/{maxLength}
          </span>
        </div>
        <button
          type="submit"
          disabled={disabled || !input.trim() || input.length > maxLength}
          className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-40 transition shrink-0"
        >
          <Send size={18} />
        </button>
      </div>
    </form>
  );
}
