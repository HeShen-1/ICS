import { create } from 'zustand';
import { sendMessage } from '../api/chat';
import type { Message, Reference } from '../api/sessions';

/** 从响应文本中移除 [追问]... 标记（追问内容通过 followup 事件单独处理） */
function stripFollowup(text: string): string {
  const idx = text.search(/\[追问\]/);
  return idx >= 0 ? text.slice(0, idx).trimEnd() : text;
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamContent: string;
  references: Reference[];
  error: string | null;
  followupSuggestions: string[];
  addUserMessage: (content: string) => void;
  sendChat: (sessionId: number, content: string) => Promise<void>;
  /** 重新生成: 移除最后一条 assistant 消息, 用最后一条 user 消息重发 */
  regenerate: (sessionId: number) => Promise<void>;
  clearStream: () => void;
  setMessages: (messages: Message[]) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamContent: '',
  references: [],
  error: null,
  followupSuggestions: [],

  addUserMessage: (content) => {
    set((s) => ({
      messages: [
        ...s.messages,
        { id: Date.now(), role: 'user', content, intent_tag: null, references: null, feedback_rating: null, created_at: new Date().toISOString() },
      ],
    }));
  },

  regenerate: async (sessionId) => {
    const { messages } = get();
    // 找最后一条 user 消息
    let lastUserIdx = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') { lastUserIdx = i; break; }
    }
    if (lastUserIdx < 0) return;

    const lastUserContent = messages[lastUserIdx].content;

    // 移除最后一条 assistant 消息(可能不存在,不报错)
    const trimmed = messages.filter((m, i) => {
      if (i > lastUserIdx && m.role === 'assistant') return false;
      return true;
    });
    set({ messages: trimmed, followupSuggestions: [] });

    // 重发
    set({ isStreaming: true, streamContent: '', references: [], error: null, followupSuggestions: [] });
    let fullText = '';
    try {
      await sendMessage(sessionId, lastUserContent, {
        onToken: (text) => {
          fullText += text;
          set({ streamContent: stripFollowup(fullText) });
        },
        onSources: (refs) => set({ references: refs }),
        onFollowup: (suggestions) => set({ followupSuggestions: suggestions }),
        onDone: (data) => {
          const state = get();
          const botMsg: Message = {
            id: data.message_id || Date.now(),
            role: 'assistant',
            content: stripFollowup(fullText),
            intent_tag: null,
            references: data.references || state.references,
            feedback_rating: null,
            created_at: new Date().toISOString(),
          };
          set((s) => ({
            messages: [...s.messages, botMsg],
            isStreaming: false,
            streamContent: '',
          }));
        },
        onError: (_code, message) => set({ error: message, isStreaming: false }),
      });
    } catch {
      set({ error: '网络连接失败，请检查网络后重试', isStreaming: false });
    }
  },

  sendChat: async (sessionId, content) => {
    set({ isStreaming: true, streamContent: '', references: [], error: null, followupSuggestions: [] });

    let fullText = '';
    try {
      await sendMessage(sessionId, content, {
        onToken: (text) => {
          fullText += text;
          set({ streamContent: stripFollowup(fullText) });
        },
        onSources: (refs) => {
          set({ references: refs });
        },
        onFollowup: (suggestions) => {
          set({ followupSuggestions: suggestions });
        },
        onDone: (data) => {
          const state = get();
          const botMsg: Message = {
            id: data.message_id || Date.now(),
            role: 'assistant',
            content: stripFollowup(fullText),
            intent_tag: null,
            references: data.references || state.references,
            feedback_rating: null,
            created_at: new Date().toISOString(),
          };
          set((s) => ({
            messages: [...s.messages, botMsg],
            isStreaming: false,
            streamContent: '',
          }));
        },
        onError: (_code, message) => {
          set({ error: message, isStreaming: false });
        },
      });
    } catch {
      set({ error: '网络连接失败，请检查网络后重试', isStreaming: false });
    }
  },

  clearStream: () => set({ streamContent: '', isStreaming: false, error: null }),
  setMessages: (messages) => set({ messages }),
}));
