package com.ragsearch.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ragsearch.client.AiServiceClient;
import com.ragsearch.domain.Document;
import com.ragsearch.dto.document.DocumentDto;
import com.ragsearch.repository.DocumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ExecutorService;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final AiServiceClient aiServiceClient;
    private final ExecutorService sseExecutor;
    private final ObjectMapper objectMapper;

    @Value("${document.chunk-size:500}")
    private int chunkSize;

    @Value("${document.chunk-overlap:50}")
    private int chunkOverlap;

    @Value("${document.allowed-extensions:.pdf,.txt,.md}")
    private String allowedExtensions;

    /**
     * 파일 업로드 처리 후 SSE로 진행 상황 전송.
     * 텍스트 추출 → 청킹 → Python AI 서비스 호출(임베딩/저장) → JPA 저장
     */
    public SseEmitter upload(MultipartFile file) {
        SseEmitter emitter = new SseEmitter(120_000L);

        sseExecutor.execute(() -> {
            try {
                validateExtension(file.getOriginalFilename());

                // 1. 텍스트 추출
                sendEvent(emitter, Map.of("stage", "extracting", "message", "텍스트 추출 중..."));
                String text = extractText(file);

                if (text.isBlank()) {
                    sendEvent(emitter, Map.of("stage", "error", "message", "텍스트를 추출할 수 없습니다."));
                    emitter.complete();
                    return;
                }

                // 2. 청크 분할
                List<String> chunks = splitText(text);
                sendEvent(emitter, Map.of(
                        "stage", "splitting",
                        "message", String.format("청크 분할 완료 (%d개)", chunks.size()),
                        "total_chunks", chunks.size()
                ));

                // 3. Python AI 서비스로 임베딩 + ChromaDB 저장 (SSE 프록시)
                String docId = UUID.randomUUID().toString();
                sendEvent(emitter, Map.of("stage", "embedding", "message", "임베딩 중... (처음 실행 시 30초 정도 소요될 수 있습니다)"));
                // heartbeat: nginx 버퍼링 방지 및 cold start 대기 중 연결 유지
                java.util.concurrent.ScheduledExecutorService heartbeatExecutor =
                        java.util.concurrent.Executors.newSingleThreadScheduledExecutor();
                heartbeatExecutor.scheduleAtFixedRate(() -> {
                    try {
                        emitter.send(SseEmitter.event().comment("heartbeat"));
                    } catch (Exception ignored) {}
                }, 5, 5, java.util.concurrent.TimeUnit.SECONDS);
                try {
                    aiServiceClient.embedAndStore(docId, file.getOriginalFilename(), chunks, emitter);
                } finally {
                    heartbeatExecutor.shutdownNow();
                }

                // 4. 문서 메타데이터 JPA 저장
                Document document = Document.builder()
                        .docId(docId)
                        .filename(file.getOriginalFilename())
                        .chunkCount(chunks.size())
                        .uploadedAt(LocalDateTime.now())
                        .build();
                documentRepository.save(document);

                // 5. 완료 이벤트
                sendEvent(emitter, Map.of(
                        "stage", "done",
                        "doc_id", docId,
                        "filename", file.getOriginalFilename(),
                        "chunk_count", chunks.size(),
                        "uploaded_at", document.getUploadedAt().toString()
                ));
                emitter.complete();

            } catch (IllegalArgumentException e) {
                sendEventQuietly(emitter, Map.of("stage", "error", "message", e.getMessage()));
                emitter.complete();
            } catch (Exception e) {
                log.error("업로드 처리 실패", e);
                emitter.completeWithError(e);
            }
        });

        return emitter;
    }

    public List<DocumentDto> listDocuments() {
        return documentRepository.findAllByOrderByUploadedAtDesc()
                .stream()
                .map(DocumentDto::from)
                .toList();
    }

    public void deleteDocument(String docId) {
        aiServiceClient.deleteVectors(docId);
        documentRepository.deleteById(docId);
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void validateExtension(String filename) {
        if (filename == null) throw new IllegalArgumentException("파일명이 없습니다.");
        String lower = filename.toLowerCase();
        boolean allowed = Arrays.stream(allowedExtensions.split(","))
                .anyMatch(lower::endsWith);
        if (!allowed) throw new IllegalArgumentException("PDF, TXT, MD 파일만 지원합니다.");
    }

    private String extractText(MultipartFile file) throws IOException {
        String filename = file.getOriginalFilename() != null ? file.getOriginalFilename().toLowerCase() : "";
        if (filename.endsWith(".pdf")) {
            try (PDDocument doc = Loader.loadPDF(file.getBytes())) {
                return new PDFTextStripper().getText(doc);
            }
        }
        return new String(file.getBytes());
    }

    /**
     * 텍스트를 chunkSize 크기로 분할. 청크 간 chunkOverlap 문자를 겹쳐서
     * 문맥이 끊기지 않게 한다.
     */
    private List<String> splitText(String text) {
        List<String> chunks = new ArrayList<>();
        int start = 0;
        while (start < text.length()) {
            int end = Math.min(start + chunkSize, text.length());
            chunks.add(text.substring(start, end).strip());
            start += chunkSize - chunkOverlap;
        }
        return chunks.stream().filter(c -> !c.isBlank()).toList();
    }

    private void sendEvent(SseEmitter emitter, Map<String, Object> data) throws IOException {
        emitter.send(SseEmitter.event().data(objectMapper.writeValueAsString(data)));
    }

    private void sendEventQuietly(SseEmitter emitter, Map<String, Object> data) {
        try { sendEvent(emitter, data); } catch (Exception ignored) {}
    }
}
