import { request } from './client';

export async function submitFeedback(
  messageId: number,
  rating: string,
  comment?: string,
): Promise<{ id: number; message: string }> {
  return request('/feedback', {
    method: 'POST',
    body: JSON.stringify({ message_id: messageId, rating, comment }),
  });
}
