package com.ragsearch.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class AiServiceClient {

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    @Value("${ai.service.url}")
    private String aiServiceUrl;

    // Render free tier cold start: nginx returns 502 immediately until the app wakes up (~30-50s)
    private static final int MAX_RETRY = 12;
    private static final long RETRY_MS = 5_000;

    private void waitForRetry(int attempt) {
        log.warn("AI 서비스 502 (cold start?), 5초 후 재시도 ({}/{})...", attempt + 1, MAX_RETRY);
        try {
            Thread.sleep(RETRY_MS);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }

    /**
     * 청크 목록을 Python AI 서비스로 보내 임베딩 후 Qdrant에 저장.
     * Python이 SSE로 진행률을 보내면 SseEmitter로 React에 프록시한다.
     */
    public void embedAndStore(String docId, String filename, List<String> chunks, SseEmitter emitter) {
        String url = aiServiceUrl + "/ai/documents/embed-and-store";
        Map<String, Object> body = Map.of(
                "doc_id", docId,
                "filename", filename,
                "chunks", chunks
        );

        for (int attempt = 0; attempt < MAX_RETRY; attempt++) {
            try {
                restTemplate.execute(url, HttpMethod.POST,
                        req -> {
                            req.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                            objectMapper.writeValue(req.getBody(), body);
                        },
                        resp -> {
                            try (BufferedReader reader = new BufferedReader(
                                    new InputStreamReader(resp.getBody()))) {
                                String line;
                                while ((line = reader.readLine()) != null) {
                                    if (line.startsWith("data: ")) {
                                        emitter.send(SseEmitter.event().data(line.substring(6)));
                                    }
                                }
                            }
                            return null;
                        }
                );
                return;
            } catch (HttpServerErrorException e) {
                if (e.getStatusCode().value() == 502 && attempt < MAX_RETRY - 1) {
                    waitForRetry(attempt);
                } else {
                    throw e;
                }
            }
        }
    }

    /**
     * 쿼리에 대한 유사 청크를 Qdrant에서 검색해 반환.
     * 동기 HTTP 호출 (블로킹). 502 시 최대 60초간 재시도.
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> searchVectors(String query, int topK) {
        String url = aiServiceUrl + "/ai/search";
        Map<String, Object> body = Map.of("query", query, "top_k", topK);

        for (int attempt = 0; attempt < MAX_RETRY; attempt++) {
            try {
                ResponseEntity<Map> response = restTemplate.postForEntity(url, body, Map.class);
                return (List<Map<String, Object>>) response.getBody().get("chunks");
            } catch (HttpServerErrorException e) {
                if (e.getStatusCode().value() == 502 && attempt < MAX_RETRY - 1) {
                    waitForRetry(attempt);
                } else {
                    throw e;
                }
            }
        }
        throw new IllegalStateException("unreachable");
    }

    /**
     * LLM 스트리밍 응답을 Python AI 서비스에서 받아 React에 프록시.
     * Python SSE: {"type":"text","content":"..."} / {"type":"done","input_tokens":N,...}
     */
    public LlmResult streamLlm(String question, List<Map<String, Object>> chunks,
                               String queryId, SseEmitter emitter) {
        String url = aiServiceUrl + "/ai/llm/stream";
        Map<String, Object> body = Map.of(
                "question", question,
                "chunks", chunks,
                "query_id", queryId
        );

        StringBuilder fullAnswer = new StringBuilder();
        int[] tokens = {0, 0}; // [inputTokens, outputTokens]

        restTemplate.execute(url, HttpMethod.POST,
                req -> {
                    req.getHeaders().setContentType(MediaType.APPLICATION_JSON);
                    objectMapper.writeValue(req.getBody(), body);
                },
                resp -> {
                    try (BufferedReader reader = new BufferedReader(
                            new InputStreamReader(resp.getBody()))) {
                        String line;
                        while ((line = reader.readLine()) != null) {
                            if (!line.startsWith("data: ")) continue;
                            String data = line.substring(6);
                            Map<String, Object> event = objectMapper.readValue(data, Map.class);
                            String type = (String) event.get("type");

                            if ("text".equals(type)) {
                                String content = (String) event.get("content");
                                fullAnswer.append(content);
                                emitter.send(SseEmitter.event().data(data));
                            } else if ("done".equals(type)) {
                                tokens[0] = (int) event.getOrDefault("input_tokens", 0);
                                tokens[1] = (int) event.getOrDefault("output_tokens", 0);
                            } else if ("error".equals(type)) {
                                emitter.send(SseEmitter.event().data(data));
                            }
                        }
                    }
                    return null;
                }
        );

        return new LlmResult(fullAnswer.toString(), tokens[0], tokens[1]);
    }

    /**
     * Qdrant에서 문서 벡터 삭제. 502 시 최대 60초간 재시도.
     */
    public void deleteVectors(String docId) {
        String url = aiServiceUrl + "/ai/documents/" + docId;
        for (int attempt = 0; attempt < MAX_RETRY; attempt++) {
            try {
                restTemplate.delete(url);
                return;
            } catch (HttpServerErrorException e) {
                if (e.getStatusCode().value() == 502 && attempt < MAX_RETRY - 1) {
                    waitForRetry(attempt);
                } else {
                    throw e;
                }
            }
        }
    }

    public record LlmResult(String answer, int inputTokens, int outputTokens) {}
}
