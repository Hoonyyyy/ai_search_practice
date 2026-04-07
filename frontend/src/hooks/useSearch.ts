import { useState } from 'react';
import { SourceChunk, QueryResponse } from '../types';
import { queryStream } from '../api/search';

export function useSearch() {
  const [question, setQuestion] = useState('');
  const [searching, setSearching] = useState(false);
  const [streamText, setStreamText] = useState('');
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState('');

  const search = async () => {
    if (!question.trim() || searching) return;

    setSearching(true);
    setStreaming(true);
    setStreamText('');
    setSources([]);
    setResult(null);
    setError('');

    try {
      await queryStream(question, 4, {
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
