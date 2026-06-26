import { create } from 'zustand';
import { sendMessage } from '../api/chat';
import type { Message, Reference } from '../api/sessions';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamContent: string;
  references: Reference[];
  error: string | null;
  followupSuggestions: string[];
  selectedKbId: number | null;

  addUserMessage: (content: string) => void;
  sendChat: (sessionId: number, content: string) => Promise<void>;
  clearStream: () => void;
  setMessages: (messages: Message[]) => void;
  setSelectedKbId: (kbId: number | null) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamContent: '',
  references: [],
  error: null,
  followupSuggestions: [],
  selectedKbId: null,

  addUserMessage: (content) => {
    set((s) => ({
      messages: [
        ...s.messages,
        { id: Date.now(), role: 'user', content, intent_tag: null, references: null, created_at: new Date().toISOString() },
      ],
    }));
  },

  sendChat: async (sessionId, content) => {
    const { selectedKbId } = get();
    set({ isStreaming: true, streamContent: '', references: [], error: null, followupSuggestions: [] });

    let fullText = '';
    try {
      await sendMessage(sessionId, content, {
        onToken: (text) => {
          fullText += text;
          set({ streamContent: fullText });
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
            content: fullText,
            intent_tag: null,
            references: data.references || state.references,
            created_at: new Date().toISOString(),
          };
          set((s) => ({
            messages: [...s.messages, botMsg],
            isStreaming: false,
            streamContent: '',
          }));
        },
        onError: (code, message) => {
          set({ error: message, isStreaming: false });
        },
      }, selectedKbId);
    } catch {
      set({ error: '网络连接失败，请检查网络后重试', isStreaming: false });
    }
  },

  clearStream: () => set({ streamContent: '', isStreaming: false, error: null }),
  setMessages: (messages) => set({ messages }),
  setSelectedKbId: (kbId) => set({ selectedKbId: kbId }),
}));
