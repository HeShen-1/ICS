import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, BookOpen, ThumbsUp, ThumbsDown, Copy, RefreshCw, Check } from 'lucide-react';
import type { Message } from '../../api/sessions';
import { SourceCard } from './SourceCard';
import { submitFeedback } from '../../api/feedback';
import { useChatStore } from '../../stores/chatStore';

interface Props {
  message: Message;
  isLastAssistant: boolean;
  sessionId: number;
}

export function ChatBubble({ message, isLastAssistant, sessionId }: Props) {
  const isUser = message.role === 'user';
  const hasRefs = !isUser && message.references && message.references.length > 0;
  const [refsOpen, setRefsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  // 从消息已持久化的 feedback_rating 初始化, 已有评价则不可更改
  const existingRating = !isUser ? message.feedback_rating ?? null : null;
  const [feedback, setFeedback] = useState<string | null>(existingRating);

  const regenerate = useChatStore((s) => s.regenerate);
  const followupSuggestions = useChatStore((s) => s.followupSuggestions);
  const isStreaming = useChatStore((s) => s.isStreaming);

  // ── 复制 ──
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback for insecure contexts
      const ta = document.createElement('textarea');
      ta.value = message.content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // ── 赞/踩 ──
  const handleFeedback = async (rating: 'positive' | 'negative') => {
    if (feedback) return;
    setFeedback(rating);
    try {
      await submitFeedback(message.id, rating);
    } catch {
      setFeedback(null);
    }
  };

  // ── 重新生成 ──
  const handleRegenerate = () => {
    regenerate(sessionId);
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} msg-enter mb-4`}>
      <div className="max-w-[80%]">
        <div className={`px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-indigo-500 text-white rounded-br-md'
            : 'bg-white border border-gray-100 shadow-sm rounded-bl-md'
        }`}>
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="markdown-body text-sm text-gray-800 prose-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* ── 参考来源（可折叠） ── */}
        {hasRefs && (
          <div className="mt-1.5">
            <button
              onClick={() => setRefsOpen(!refsOpen)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-indigo-500 transition-colors"
            >
              {refsOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <BookOpen size={11} />
              <span>参考 {message.references!.length} 篇文档</span>
            </button>
            {refsOpen && (
              <div className="mt-1.5 space-y-1">
                {message.references!.map((ref, i) => (
                  <SourceCard key={i} docName={ref.doc_name} snippet={ref.snippet} score={ref.score} kbName={ref.kb_name} />
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── 操作按钮栏（仅 AI 消息） ── */}
        {!isUser && (
          <div className="flex items-center gap-0.5 mt-1.5 ml-1">
            {/* 复制 */}
            <button
              onClick={handleCopy}
              className="p-1 rounded text-gray-300 hover:text-indigo-500 transition-colors"
              title="复制回答"
            >
              {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
            </button>

            {/* 赞 */}
            <button
              onClick={() => handleFeedback('positive')}
              disabled={!!feedback}
              className={`p-1 rounded transition-colors ${
                feedback === 'positive' ? 'text-green-600' : 'text-gray-300 hover:text-green-500'
              }`}
              title="有帮助"
            >
              <ThumbsUp size={14} />
            </button>

            {/* 踩 */}
            <button
              onClick={() => handleFeedback('negative')}
              disabled={!!feedback}
              className={`p-1 rounded transition-colors ${
                feedback === 'negative' ? 'text-red-600' : 'text-gray-300 hover:text-red-500'
              }`}
              title="无帮助"
            >
              <ThumbsDown size={14} />
            </button>

            {/* 重新生成 */}
            {isLastAssistant && (
              <button
                onClick={handleRegenerate}
                disabled={isStreaming}
                className="p-1 rounded text-gray-300 hover:text-indigo-500 transition-colors disabled:opacity-40"
                title="重新生成"
              >
                <RefreshCw size={14} />
              </button>
            )}

            {feedback && <span className="text-xs text-gray-400 ml-1">感谢反馈</span>}
          </div>
        )}

        {/* ── 追问（仅最后一条 AI 消息，按钮下方竖排） ── */}
        {!isUser && isLastAssistant && followupSuggestions.length > 0 && (
          <div className="mt-2 flex flex-col gap-1">
            {followupSuggestions.map((q, i) => (
              <button
                key={i}
                onClick={() => {
                  // 通过 chatStore 发送，需要从父组件回调
                  window.dispatchEvent(new CustomEvent('sendFollowup', { detail: q }));
                }}
                className="text-left px-3 py-1.5 text-xs text-indigo-600 bg-indigo-50/60 border border-indigo-100 rounded-lg hover:bg-indigo-100 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* ── 意图标签 ── */}
        {message.intent_tag && (
          <span className="inline-block mt-1 text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">
            {message.intent_tag}
          </span>
        )}
      </div>
    </div>
  );
}
