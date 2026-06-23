import { create } from 'zustand';
import { sendMessage } from '../api/chat';
import type { Message, Reference } from '../api/sessions';

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  streamContent: string;
  references: Reference[];
  error: string | null;

  addUserMessage: (content: string) => void;
  sendChat: (sessionId: number, content: string) => Promise<void>;
  clearStream: () => void;
  setMessages: (messages: Message[]) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamContent: '',
  references: [],
  error: null,

  addUserMessage: (content) => {
    set((s) => ({
      messages: [
        ...s.messages,
        { id: Date.now(), role: 'user', content, intent_tag: null, references: null, created_at: new Date().toISOString() },
      ],
    }));
  },

  sendChat: async (sessionId, content) => {
    set({ isStreaming: true, streamContent: '', references: [], error: null });

    let fullText = '';
    await sendMessage(sessionId, content, {
      onToken: (text) => {
        fullText += text;
        set({ streamContent: fullText });
      },
      onSources: (refs) => {
        set({ references: refs });
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
    });
  },

  clearStream: () => set({ streamContent: '', isStreaming: false, error: null }),
  setMessages: (messages) => set({ messages }),
}));
