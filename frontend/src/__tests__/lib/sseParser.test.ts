import { describe, it, expect } from 'vitest';
import { parseSSEChunk } from '../../lib/sseParser';

describe('parseSSEChunk', () => {
  describe('single events', () => {
    it('parses a single token event', () => {
      const input = 'event: token\ndata: {"text":"你好"}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(1);
      expect(result.events[0].event).toBe('token');
      expect(result.events[0].data).toEqual({ text: '你好' });
      expect(result.remainder).toBe('');
    });

    it('parses a sources event', () => {
      const input = 'event: sources\ndata: {"references":[{"doc_name":"test.pdf","snippet":"...","score":0.9}]}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(1);
      expect(result.events[0].event).toBe('sources');
      expect(result.events[0].data.references).toHaveLength(1);
      expect(result.events[0].data.references[0]).toEqual({
        doc_name: 'test.pdf',
        snippet: '...',
        score: 0.9,
      });
      expect(result.remainder).toBe('');
    });

    it('parses a done event', () => {
      const input = 'event: done\ndata: {"message_id":42}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(1);
      expect(result.events[0].event).toBe('done');
      expect(result.events[0].data).toEqual({ message_id: 42 });
      expect(result.remainder).toBe('');
    });

    it('parses an error event', () => {
      const input = 'event: error\ndata: {"code":"RATE_LIMIT","message":"请求过于频繁"}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(1);
      expect(result.events[0].event).toBe('error');
      expect(result.events[0].data).toEqual({ code: 'RATE_LIMIT', message: '请求过于频繁' });
      expect(result.remainder).toBe('');
    });

    it('parses a followup event', () => {
      const input = 'event: followup\ndata: {"suggestions":["再详细一点","举个例子","总结一下"]}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(1);
      expect(result.events[0].event).toBe('followup');
      expect(result.events[0].data).toEqual({
        suggestions: ['再详细一点', '举个例子', '总结一下'],
      });
      expect(result.remainder).toBe('');
    });
  });

  describe('multiple events', () => {
    it('parses multiple events in one buffer', () => {
      const input =
        'event: token\ndata: {"text":"Hello"}\n\n' +
        'event: token\ndata: {"text":" World"}\n\n' +
        'event: sources\ndata: {"references":[]}\n\n' +
        'event: done\ndata: {"message_id":1}\n\n';

      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(4);
      expect(result.events[0].event).toBe('token');
      expect(result.events[0].data).toEqual({ text: 'Hello' });
      expect(result.events[1].event).toBe('token');
      expect(result.events[1].data).toEqual({ text: ' World' });
      expect(result.events[2].event).toBe('sources');
      expect(result.events[3].event).toBe('done');
      expect(result.remainder).toBe('');
    });

    it('returns empty events array for empty input', () => {
      const result = parseSSEChunk('');
      expect(result.events).toHaveLength(0);
      expect(result.remainder).toBe('');
    });
  });

  describe('partial events', () => {
    it('returns incomplete event as remainder', () => {
      const input = 'event: token\ndata: {"text":"Hello"}\n\nevent: token\ndata: {"text":"Wor';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(1);
      expect(result.events[0].data).toEqual({ text: 'Hello' });
      expect(result.remainder).toBe('event: token\ndata: {"text":"Wor');
    });

    it('handles only partial data with no complete events', () => {
      const input = 'event: token\ndata: {"text"';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(0);
      expect(result.remainder).toBe('event: token\ndata: {"text"');
    });

    it('handles continuation: remainder from previous + new chunk completes event', () => {
      const chunk1 = 'event: token\ndata: {"text":"Hel';
      const result1 = parseSSEChunk(chunk1);
      expect(result1.events).toHaveLength(0);
      expect(result1.remainder).toBe('event: token\ndata: {"text":"Hel');

      const chunk2 = result1.remainder + 'lo"}\n\n';
      const result2 = parseSSEChunk(chunk2);
      expect(result2.events).toHaveLength(1);
      expect(result2.events[0].event).toBe('token');
      expect(result2.events[0].data).toEqual({ text: 'Hello' });
      expect(result2.remainder).toBe('');
    });
  });

  describe('edge cases', () => {
    it('skips malformed JSON data', () => {
      const input = 'event: token\ndata: {invalid json}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(0);
      expect(result.remainder).toBe('');
    });

    it('skips entries with no event field', () => {
      const input = 'data: {"text":"no event"}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(0);
    });

    it('skips entries with no data field', () => {
      const input = 'event: token\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(0);
    });

    it('skips empty lines between events', () => {
      const input = 'event: token\ndata: {"text":"a"}\n\n\n\nevent: token\ndata: {"text":"b"}\n\n';
      const result = parseSSEChunk(input);

      expect(result.events).toHaveLength(2);
    });

    it('handles whitespace-only input', () => {
      const result = parseSSEChunk('   \n\n   ');
      expect(result.events).toHaveLength(0);
      // The second segment (after the last \n\n) becomes the remainder
      expect(result.remainder).toBe('   ');
    });
  });
});
