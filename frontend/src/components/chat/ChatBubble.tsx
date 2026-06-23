import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../../api/sessions';
import { SourceCard } from './SourceCard';
import { FeedbackBar } from './FeedbackBar';

interface Props {
  message: Message;
}

export function ChatBubble({ message }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} msg-enter mb-4`}>
      <div className="max-w-[80%]">
        <div className={`px-4 py-3 rounded-2xl ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
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

        {!isUser && message.references && message.references.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.references.map((ref, i) => (
              <SourceCard key={i} docName={ref.doc_name} snippet={ref.snippet} score={ref.score} />
            ))}
          </div>
        )}

        {!isUser && <FeedbackBar messageId={message.id} />}

        {message.intent_tag && (
          <span className="inline-block mt-1 text-xs px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full">
            {message.intent_tag}
          </span>
        )}
      </div>
    </div>
  );
}
