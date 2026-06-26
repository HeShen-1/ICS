export interface SSEParsedEvent {
  event: string;
  data: Record<string, unknown>;
}

export interface SSEParseResult {
  events: SSEParsedEvent[];
  remainder: string;
}

/**
 * Parse a chunk of SSE (text/event-stream) text.
 * Returns parsed events and any incomplete remainder for the next chunk.
 */
export function parseSSEChunk(chunk: string): SSEParseResult {
  const events: SSEParsedEvent[] = [];
  const parts = chunk.split('\n\n');
  const remainder = parts.pop() || '';

  for (const part of parts) {
    if (!part.trim()) continue;

    const eventMatch = part.match(/^event: (\w+)$/m);
    const dataMatch = part.match(/^data: (.+)$/m);

    if (!eventMatch || !dataMatch) continue;

    try {
      const data = JSON.parse(dataMatch[1]);
      events.push({ event: eventMatch[1], data });
    } catch {
      // Skip malformed JSON events
    }
  }

  return { events, remainder };
}
