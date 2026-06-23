import { useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { SessionList } from '../components/sidebar/SessionList';
import { ChatBubble } from '../components/chat/ChatBubble';
import { ChatInput } from '../components/chat/ChatInput';
import { StreamingText } from '../components/chat/StreamingText';
import { useChatStore } from '../stores/chatStore';
import { getSession } from '../api/sessions';

export function ChatPage() {
  const { sessionId } = useParams();
  const { messages, isStreaming, streamContent, error, setMessages, addUserMessage, sendChat } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (sessionId) {
      getSession(Number(sessionId))
        .then((s) => setMessages(s.messages || []))
        .catch(() => setMessages([]));
    } else {
      setMessages([]);
    }
  }, [sessionId, setMessages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  const handleSend = async (content: string) => {
    if (!sessionId) return;
    addUserMessage(content);
    await sendChat(Number(sessionId), content);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <SessionList />
      <div className="flex-1 flex flex-col">
        <div className="h-14 border-b border-gray-200 bg-white flex items-center px-6">
          <h2 className="text-sm font-medium text-gray-700">
            {sessionId ? `会话 #${sessionId}` : '新会话'}
          </h2>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 && !isStreaming && (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              输入问题开始对话
            </div>
          )}

          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}

          {isStreaming && <StreamingText content={streamContent} />}

          {error && (
            <div className="flex justify-center mb-4">
              <p className="text-red-500 text-sm bg-red-50 px-4 py-2 rounded-lg">{error}</p>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <ChatInput onSend={handleSend} disabled={isStreaming || !sessionId} />
      </div>
    </div>
  );
}
