import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { SessionList } from '../components/sidebar/SessionList';
import { ChatBubble } from '../components/chat/ChatBubble';
import { ChatInput } from '../components/chat/ChatInput';
import { StreamingText } from '../components/chat/StreamingText';
import { useChatStore } from '../stores/chatStore';
import { getSession, createSession } from '../api/sessions';
import { useSessionStore } from '../stores/sessionStore';

export function ChatPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { messages, isStreaming, streamContent, error, setMessages, addUserMessage, sendChat } = useChatStore();
  const addSession = useSessionStore((s) => s.addSession);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [creating, setCreating] = useState(false);

  // 加载已有会话
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

  // 监听追问点击事件（从 ChatBubble 发出）
  useEffect(() => {
    const handler = (e: Event) => {
      const q = (e as CustomEvent).detail as string;
      handleSend(q);
    };
    window.addEventListener('sendFollowup', handler);
    return () => window.removeEventListener('sendFollowup', handler);
  }, [sessionId]);

  const handleSend = async (content: string) => {
    let sid = sessionId ? Number(sessionId) : null;

    // 首条消息: 先创建会话 → 发送消息(后端自动命名) → 最后跳转
    if (!sid) {
      setCreating(true);
      try {
        const s = await createSession();
        addSession(s);
        sid = s.id;
        // 先发消息再跳转, 避免 navigate 触发 useEffect 清空本地状态
        addUserMessage(content);
        await sendChat(sid, content);
        navigate(`/chat/${s.id}`, { replace: true });
      } catch {
        // ignore
      }
      setCreating(false);
      return;
    }

    addUserMessage(content);
    await sendChat(sid, content);
  };

  const numId = sessionId ? Number(sessionId) : 0;

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

          {messages.map((msg, i) => (
            <ChatBubble
              key={msg.id}
              message={msg}
              isLastAssistant={
                !isStreaming
                && msg.role === 'assistant'
                && i === messages.length - 1
              }
              sessionId={numId}
            />
          ))}

          {isStreaming && <StreamingText content={streamContent} />}

          {error && (
            <div className="flex justify-center mb-4">
              <p className="text-red-500 text-sm bg-red-50 px-4 py-2 rounded-lg">{error}</p>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <ChatInput onSend={handleSend} disabled={isStreaming || creating} />
      </div>
    </div>
  );
}
