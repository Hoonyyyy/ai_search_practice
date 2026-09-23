export interface DocumentInfo {
  doc_id: string;
  filename: string;
  chunk_count: number;
  uploaded_at: string;
  sample: boolean;    // 예시 문서 (서버에서 판단함)
}

export interface SourceChunk {
  doc_id: string;
  filename: string;
  content_preview: string;
}

export interface QueryMetrics {
  query_id: string;
  response_time_ms: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  retrieved_chunks: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceChunk[];
  metrics: QueryMetrics;
}

export interface MetricsSummary {
  total_queries: number;
  median_response_time_ms: number;
  total_tokens_used: number;
}

export interface TimelinePoint {
  timestamp: string;
  response_time_ms: number;
  total_tokens: number;
}

export interface QueryLog {
  id: string;
  timestamp: string;
  question: string;
  answer: string;
  response_time_ms: number;
  total_tokens: number;
}
