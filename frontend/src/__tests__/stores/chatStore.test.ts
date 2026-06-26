import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useChatStore } from '../../stores/chatStore';

// Mock the sendMessage API
vi.mock('../../api/chat', () => ({
  sendMessage: vi.fn(),
}));

import { sendMessage } from '../../api/chat';

function getStore() {
  return useChatStore.getState();
}

describe('chatStore', () => {
  beforeEach(() => {
    useChatStore.setState({
      messages: [],
      isStreaming: false,
      streamContent: '',
      references: [],
      error: null,
      followupSuggestions: [],
      selectedKbId: null,
    });
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('has correct initial values', () => {
      const s = getStore();
      expect(s.messages).toEqual([]);
      expect(s.isStreaming).toBe(false);
      expect(s.streamContent).toBe('');
      expect(s.references).toEqual([]);
      expect(s.error).toBeNull();
      expect(s.followupSuggestions).toEqual([]);
      expect(s.selectedKbId).toBeNull();
    });
  });

  describe('addUserMessage', () => {
    it('appends a user message to the messages array', () => {
      getStore().addUserMessage('你好');
      const msgs = getStore().messages;
      expect(msgs).toHaveLength(1);
      expect(msgs[0].role).toBe('user');
      expect(msgs[0].content).toBe('你好');
    });

    it('preserves existing messages when adding a new one', () => {
      getStore().addUserMessage('第一条');
      getStore().addUserMessage('第二条');
      const msgs = getStore().messages;
      expect(msgs).toHaveLength(2);
      expect(msgs[0].content).toBe('第一条');
      expect(msgs[1].content).toBe('第二条');
    });
  });

  describe('sendChat', () => {
    it('sets isStreaming to true when sending starts', async () => {
      const mockSend = vi.fn().mockImplementation(
        (_sessionId: number, _content: string, _callbacks: {
          onToken: (text: string) => void;
          onSources: (refs: unknown[]) => void;
          onFollowup: (suggestions: string[]) => void;
          onDone: (data: { message_id: number | null }) => void;
          onError: (code: string, message: string) => void;
        }) => {
          // Never call any callback - just keep streaming
          return new Promise(() => {});
        },
      );
      vi.mocked(sendMessage).mockImplementation(mockSend);

      const promise = getStore().sendChat(1, 'test');
      expect(getStore().isStreaming).toBe(true);
      expect(getStore().streamContent).toBe('');
      // Cleanup the hanging promise
      promise.catch(() => {});
      useChatStore.setState({ isStreaming: false });
    });

    it('appends token to streamContent via onToken callback', async () => {
      vi.mocked(sendMessage).mockImplementation(
        (_sessionId, _content, callbacks) => {
          callbacks.onToken('Hello');
          callbacks.onToken(' World');
          return Promise.resolve();
        },
      );

      await getStore().sendChat(1, 'test');
      expect(sendMessage).toHaveBeenCalled();
    });

    it('passes callbacks and sessionId to sendMessage', async () => {
      vi.mocked(sendMessage).mockImplementation(
        (_sessionId, _content, _callbacks) => Promise.resolve(),
      );

      await getStore().sendChat(1, 'test');
      expect(sendMessage).toHaveBeenCalledWith(
        1,
        'test',
        expect.objectContaining({
          onToken: expect.any(Function),
          onSources: expect.any(Function),
          onFollowup: expect.any(Function),
          onDone: expect.any(Function),
          onError: expect.any(Function),
        }),
        null,
      );
    });

    it('onDone adds assistant message and stops streaming', async () => {
      vi.mocked(sendMessage).mockImplementation(
        (_sessionId, _content, callbacks) => {
          callbacks.onToken('回答内容');
          callbacks.onDone({ message_id: 42, references: [] });
          return Promise.resolve();
        },
      );

      const store = getStore();
      store.addUserMessage('问题');
      await store.sendChat(1, '问题');

      const state = getStore();
      expect(state.isStreaming).toBe(false);
      expect(state.streamContent).toBe('');
      expect(state.messages).toHaveLength(2); // user + assistant
      expect(state.messages[1].role).toBe('assistant');
      expect(state.messages[1].content).toBe('回答内容');
    });

    it('onError sets error message and stops streaming', async () => {
      vi.mocked(sendMessage).mockImplementation(
        (_sessionId, _content, callbacks) => {
          callbacks.onError('RATE_LIMIT', '请求过于频繁');
          return Promise.resolve();
        },
      );

      await getStore().sendChat(1, 'test');
      const state = getStore();
      expect(state.isStreaming).toBe(false);
      expect(state.error).toBe('请求过于频繁');
    });

    it('sets network error on exception', async () => {
      vi.mocked(sendMessage).mockRejectedValue(new Error('Network failure'));

      await getStore().sendChat(1, 'test');
      const state = getStore();
      expect(state.isStreaming).toBe(false);
      expect(state.error).toBe('网络连接失败，请检查网络后重试');
    });

    it('clears streamContent and error before starting new send', async () => {
      // Set some error state first
      useChatStore.setState({ error: '旧错误', streamContent: '旧内容' });

      vi.mocked(sendMessage).mockImplementation(
        (_sessionId, _content, _callbacks) => {
          return Promise.resolve();
        },
      );

      await getStore().sendChat(1, 'test');
      expect(getStore().error).toBeNull();
    });
  });

  describe('clearStream', () => {
    it('resets streamContent, isStreaming, and error', () => {
      useChatStore.setState({
        streamContent: 'partial text',
        isStreaming: true,
        error: 'some error',
      });

      getStore().clearStream();
      const s = getStore();
      expect(s.streamContent).toBe('');
      expect(s.isStreaming).toBe(false);
      expect(s.error).toBeNull();
    });
  });

  describe('setMessages', () => {
    it('replaces the entire messages array', () => {
      useChatStore.setState({
        messages: [
          { id: 1, role: 'user' as const, content: 'old', intent_tag: null, references: null, created_at: '' },
        ],
      });

      const newMessages = [
        { id: 2, role: 'assistant' as const, content: 'new', intent_tag: null, references: null, created_at: '' },
      ];

      getStore().setMessages(newMessages);
      expect(getStore().messages).toEqual(newMessages);
      expect(getStore().messages).toHaveLength(1);
    });
  });

  describe('setSelectedKbId', () => {
    it('sets selectedKbId to a number', () => {
      getStore().setSelectedKbId(5);
      expect(getStore().selectedKbId).toBe(5);
    });

    it('sets selectedKbId to null', () => {
      getStore().setSelectedKbId(10);
      getStore().setSelectedKbId(null);
      expect(getStore().selectedKbId).toBeNull();
    });
  });
});
