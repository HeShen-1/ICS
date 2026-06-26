import { BASE_URL } from './client';

export type SSECallback = {
  onToken: (text: string) => void;
  onSources: (references: Reference[]) => void;
  onFollowup: (suggestions: string[]) => void;
  onDone: (data: { message_id: number | null; references?: Reference[] }) => void;
  onError: (code: string, message: string) => void;
};

interface Reference {
  doc_name: string;
  snippet: string;
  score: number;
}

export async function sendMessage(
  sessionId: number,
  content: string,
  callbacks: SSECallback,
  kbId?: number | null,
): Promise<void> {
  const token = localStorage.getItem('token');

  const body: Record<string, unknown> = { content };
  if (kbId !== undefined && kbId !== null) {
    body.kb_id = kbId;
  }

  const response = await fetch(`${BASE_URL}/chat/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '请求失败' }));
    callbacks.onError('HTTP_ERROR', error.detail || '请求失败');
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError('STREAM_ERROR', '无法读取流');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() || '';

    for (const part of parts) {
      if (!part.trim()) continue;

      const eventMatch = part.match(/^event: (\w+)$/m);
      const dataMatch = part.match(/^data: (.+)$/m);

      if (!eventMatch || !dataMatch) continue;

      const event = eventMatch[1];
      try {
        const data = JSON.parse(dataMatch[1]);

        switch (event) {
          case 'token':
            callbacks.onToken(data.text);
            break;
          case 'sources':
            callbacks.onSources(data.references || []);
            break;
          case 'followup':
            callbacks.onFollowup(data.suggestions || []);
            break;
          case 'done':
            callbacks.onDone(data);
            break;
          case 'error':
            callbacks.onError(data.code, data.message);
            break;
        }
      } catch {
        // Skip malformed events
      }
    }
  }

  // Flush residual buffer
  if (buffer.trim()) {
    const eventMatch = buffer.match(/^event: (\w+)$/m);
    const dataMatch = buffer.match(/^data: (.+)$/m);
    if (eventMatch && dataMatch) {
      try {
        const data = JSON.parse(dataMatch[1]);
        switch (eventMatch[1]) {
          case 'token':
            callbacks.onToken(data.text);
            break;
          case 'sources':
            callbacks.onSources(data.references || []);
            break;
          case 'followup':
            callbacks.onFollowup(data.suggestions || []);
            break;
          case 'done':
            callbacks.onDone(data);
            break;
          case 'error':
            callbacks.onError(data.code, data.message);
            break;
        }
      } catch {
        // Skip malformed residual events
      }
    }
  }
}
