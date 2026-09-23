import { useState } from 'react';
import { SourceChunk, QueryResponse } from '../types';
import { queryStream } from '../api/search';
import { wakeAiService } from '../api/server';

export function useSearch() {
  const [question, setQuestion] = useState('');
  const [searching, setSearching] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');

  // 칩을 누르면 입력창 상태가 갱신되기 전에 검색이 시작될 수 있다.
  // 그래서 질문을 직접 받을 수 있게 열어둔다 (없으면 기존처럼 입력창 값을 쓴다).
  const search = async (override?: string) => {
    const q = (override ?? question).trim();
    if (!q || searching) return;
    if (override) setQuestion(override);

    wakeAiService();
    setSearching(true);
    setStreaming(true);
    setStreamText('');
    setSources([]);
    setResult(null);
    setError('');

    try {
      await queryStream(q, 4, {
        onMeta: (queryId, srcs) => setSources(srcs),
        onToken: (token) => setStreamText((prev) => prev + token),
        onError: (msg) => setError(msg),
        onDone: (metrics) => {
          setStreaming(false);
          setResult({
            answer: '',
            sources: [],
            metrics: {
              query_id: '',
              total_tokens: metrics.input_tokens + metrics.output_tokens,
              ...metrics,
            },
          });
        },
      });
    } catch {
      setError('검색 중 오류가 발생했습니다.');
    } finally {
      setSearching(false);
      setStreaming(false);
    }
  };

  return { question, setQuestion, searching, streamText, sources, result, streaming, error, search };
}
