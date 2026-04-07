package com.ragsearch.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragsearch.client.AiServiceClient;
import com.ragsearch.domain.QueryLog;
import com.ragsearch.repository.QueryLogRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ExecutorService;

@Slf4j
@Service
@RequiredArgsConstructor
public class SearchService {

    private final QueryLogRepository queryLogRepository;
    private final AiServiceClient aiServiceClient;
    private final ExecutorService sseExecutor;
    private final ObjectMapper objectMapper;

    /**
     * 질문에 대한 RAG 검색 및 LLM 응답을 SSE 스트리밍.
     *
     * 흐름:
     * 1. Python AI 서비스로 벡터 검색 (동기 HTTP)
     * 2. 메타 이벤트 전송 (출처 정보)
     * 3. Python AI 서비스로 LLM 스트리밍 (SSE 프록시)
     * 4. 쿼리 로그 JPA 저장
     * 5. 완료 이벤트 전송
     */
    public SseEmitter query(String question, int topK) {
        SseEmitter emitter = new SseEmitter(120_000L);

        sseExecutor.execute(() -> {
            String queryId = UUID.randomUUID().toString();
            long startMs = System.currentTimeMillis();

            try {
                // 1. 벡터 유사도 검색
                List<Map<String, Object>> chunks = aiServiceClient.searchVectors(question, topK);

                if (chunks.isEmpty()) {
                    sendEvent(emitter, Map.of("type", "meta", "query_id", queryId, "sources", List.of()));
                    sendEvent(emitter, Map.of("type", "text", "content", "업로드된 문서가 없습니다. 먼저 문서를 업로드해주세요."));
                    sendEvent(emitter, Map.of("type", "done", "response_time_ms", 0,
                            "input_tokens", 0, "output_tokens", 0, "retrieved_chunks", 0));
                    emitter.complete();
                    return;
                }

                // 2. 출처 정보 전송
                List<Map<String, Object>> sources = chunks.stream().map(c -> {
                    Map<String, Object> meta = (Map<String, Object>) c.get("metadata");
                    String content = (String) c.get("content");
                    return Map.<String, Object>of(
                            "doc_id", meta.getOrDefault("doc_id", ""),
                            "filename", meta.getOrDefault("filename", ""),
                            "content_preview", content.length() > 150
                                    ? content.substring(0, 150) + "..." : content
                    );
                }).toList();
                sendEvent(emitter, Map.of("type", "meta", "query_id", queryId, "sources", sources));

                // 3. LLM 스트리밍 (SSE 프록시)
                AiServiceClient.LlmResult result = aiServiceClient.streamLlm(question, chunks, queryId, emitter);

                // 4. 쿼리 로그 저장
                int responseTimeMs = (int) (System.currentTimeMillis() - startMs);
                queryLogRepository.save(QueryLog.builder()
                        .id(queryId)
                        .timestamp(LocalDateTime.now())
                        .question(question)
                        .answer(result.answer())
                        .responseTimeMs(responseTimeMs)
                        .inputTokens(result.inputTokens())
                        .outputTokens(result.outputTokens())
                        .totalTokens(result.inputTokens() + result.outputTokens())
                        .retrievedChunks(chunks.size())
                        .build());

                // 5. 완료 이벤트
                sendEvent(emitter, Map.of(
                        "type", "done",
                        "response_time_ms", responseTimeMs,
                        "input_tokens", result.inputTokens(),
                        "output_tokens", result.outputTokens(),
                        "retrieved_chunks", chunks.size()
                ));
                emitter.complete();

            } catch (Exception e) {
                log.error("검색 처리 실패", e);
                sendEventQuietly(emitter, Map.of("type", "error",
                        "content", "검색 중 오류가 발생했습니다: " + e.getMessage()));
                emitter.complete();
            }
        });

        return emitter;
    }

    public void saveFeedback(String queryId, double score) {
        queryLogRepository.findById(queryId).ifPresent(log -> {
            log.updateScore(score);
            queryLogRepository.save(log);
        });
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> toMap(Object o) {
        return (Map<String, Object>) o;
    }

    private void sendEvent(SseEmitter emitter, Map<String, Object> data) throws IOException {
        emitter.send(SseEmitter.event().data(objectMapper.writeValueAsString(data)));
    }

    private void sendEventQuietly(SseEmitter emitter, Map<String, Object> data) {
        try { sendEvent(emitter, data); } catch (Exception ignored) {}
    }
}
