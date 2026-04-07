import { SourceChunk, QueryMetrics } from '../types';

const BASE = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:8080/api';

export interface StreamCallbacks {
  onMeta: (queryId: string, sources: SourceChunk[]) => void;
  onToken: (token: string) => void;
  onError?: (message: string) => void;
  onDone: (metrics: Omit<QueryMetrics, 'query_id' | 'total_tokens'>) => void;
}

export const queryStream = async (question: string, topK = 4, callbacks: StreamCallbacks): Promise<void> => {
  const resp = await fetch(`${BASE}/search/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  });

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const json = JSON.parse(line.slice(6));
      if (json.type === 'meta') {
        callbacks.onMeta(json.query_id, json.sources);
      } else if (json.type === 'text') {
        callbacks.onToken(json.content);
      } else if (json.type === 'error') {
        callbacks.onError?.(json.content);
      } else if (json.type === 'done') {
        callbacks.onDone({
          response_time_ms: json.response_time_ms,
          input_tokens: json.input_tokens,
          output_tokens: json.output_tokens,
          retrieved_chunks: json.retrieved_chunks,
        });
      }
    }
  }
};

export const sendFeedback = async (queryId: string, score: number): Promise<void> => {
  await fetch(`${BASE}/search/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query_id: queryId, score }),
  });
};
