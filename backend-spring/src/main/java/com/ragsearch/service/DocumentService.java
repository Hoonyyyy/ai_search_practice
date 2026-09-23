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
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final AiServiceClient aiServiceClient;
    private final ThreadPoolExecutor uploadExecutor;
    private final ObjectMapper objectMapper;

    // 제출됐지만 아직 끝나지 않은 업로드 수 (대기 중 포함). 스레드 상태를 묻지 않고 직접 센다.
    private final AtomicInteger uploadsInFlight = new AtomicInteger();

    @Value("${document.chunk-size:500}")
    private int chunkSize;

    @Value("${document.chunk-overlap:50}")
    private int chunkOverlap;

    @Value("${document.allowed-extensions:.pdf,.txt,.md}")
    private String allowedExtensions;

    @Value("${document.ttl-minutes:60}")
    private int ttlMinutes;

    /** 삭제 요청의 결과. 컨트롤러가 상태 코드를 고르는 근거가 된다. */
    public enum DeleteResult { DELETED, NOT_FOUND, SAMPLE_PROTECTED }

    /**
     * 파일 업로드 처리 후 SSE로 진행 상황 전송.
     * 텍스트 추출 → 청킹 → Python AI 서비스 호출(임베딩/저장) → JPA 저장
     */
    public SseEmitter upload(MultipartFile file, String sessionId) {
        SseEmitter emitter = new SseEmitter(300_000L);

        // 세션 없는 업로드를 허용하면 owner 가 NULL 로 저장된다 = "예시 문서"가 돼버리고,
        // 예시 문서는 아무도 지울 수 없다(아래 deleteDocument 참고). 그래서 여기서 막는다.
        if (sessionId == null || sessionId.isBlank()) {
            sendEventQuietly(emitter, Map.of("stage", "error",
                    "message", "세션 정보가 없습니다. 새로고침 후 다시 시도해 주세요."));
            emitter.complete();
            return emitter;
        }

        // 앞에 3개가 이미 있으면 이 업로드는 줄을 선다 — 멈춘 게 아니라 기다리는 중임을 알린다
        if (uploadsInFlight.incrementAndGet() > uploadExecutor.getMaximumPoolSize()) {
            sendEventQuietly(emitter, Map.of("stage", "queued", "message", "앞선 업로드가 끝나길 기다리는 중..."));
        }

        uploadExecutor.execute(() -> {
            try {
                processUpload(file, sessionId, emitter);
            } finally {
                uploadsInFlight.decrementAndGet();
            }
        });

        return emitter;
    }

    /** 텍스트 추출 → 청킹 → Python AI 서비스 호출(임베딩/저장) → JPA 저장 */
    private void processUpload(MultipartFile file, String sessionId, SseEmitter emitter) {

        long t0 = System.currentTimeMillis();

        try {
            validateExtension(file.getOriginalFilename());

            // 1. 텍스트 추출
            sendEvent(emitter, Map.of("stage", "extracting", "message", "텍스트 추출 중..."));
            String text = extractText(file);

            long tExtract = System.currentTimeMillis();

            if (text.isBlank()) {
                sendEvent(emitter, Map.of("stage", "error", "message", "텍스트를 추출할 수 없습니다."));
                emitter.complete();
                return;
            }

            // 2. 청크 분할
            List<String> chunks = splitText(text, chunkSize, chunkOverlap);

            long tSplit = System.currentTimeMillis();

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
                aiServiceClient.embedAndStore(docId, file.getOriginalFilename(), chunks, sessionId, emitter);
            } catch (Exception e) {
                cleanupLeftoverVectors(docId);
                throw e;
            } finally {
                heartbeatExecutor.shutdownNow();
            }

            long tEmbed = System.currentTimeMillis();

            // 4. 문서 메타데이터 JPA 저장
            Document document = Document.builder()
                    .docId(docId)
                    .filename(file.getOriginalFilename())
                    .chunkCount(chunks.size())
                    .uploadedAt(LocalDateTime.now())
                    .owner(sessionId)
                    .build();
            documentRepository.save(document);

            // 세션당 문서 1개 - 새 문서가 확실히 저장된 뒤에 옛 문서를 지운다.
            replaceOlderDocuments(sessionId, docId);

            log.info("upload timing -> extract {}ms,  split {}ms, embed {}ms, total {}ms ({} chunks, textLen {}, longest {})",
                    tExtract - t0,
                    tSplit - tExtract,
                    tEmbed - tSplit,
                    tEmbed - t0,
                    chunks.size(),
                    text.length(),
                    chunks.stream().mapToInt(String::length).max().orElse(0)
                );


            // 5. 완료 이벤트
            sendEvent(emitter, Map.of(
                    "stage", "done",
                    "doc_id", docId,
                    "filename", file.getOriginalFilename(),
                    "chunk_count", chunks.size(),
                    "uploaded_at", document.getUploadedAt().toString()
            ));
            emitter.complete();

        } catch (InvalidUploadException e) {
            sendEventQuietly(emitter, Map.of("stage", "error", "message", e.getMessage()));
            emitter.complete();
        } catch (Exception e) {
            if (ErrorMessages.isClientGone(e)) {
                log.info("사용자가 연결을 끊어 업로드를 취소했습니다");
            } else {
                log.error("업로드 처리 실패", e);
                sendEventQuietly(emitter, Map.of("stage", "error", "message", ErrorMessages.forUpload(e)));
            }
            emitter.complete();
        }
    }


    /**
     * 이 세션이 올린 문서를 보여준다. 없으면 예시 문서를 대신 보여준다 —
     * 아무것도 올리지 않은 방문자도 바로 검색을 시험해볼 수 있게.
     * 헤더가 없는 요청(keep-alive 핑 등)도 에러 없이 예시 문서를 받는다.
     *
     * @param sessionId 익명 세션 id. 없으면 null
     * @return 화면에 보여줄 문서 목록
     */
    public List<DocumentDto> listDocuments(String sessionId) {
        List<Document> mine = sessionId == null
                ? List.of()
                : documentRepository.findAllByOwnerAndUploadedAtAfterOrderByUploadedAtDesc(sessionId, aliveSince());

        List<Document> visible = mine.isEmpty()
                ? documentRepository.findAllByOwnerIsNullOrderByUploadedAtDesc()
                : mine;

        return visible.stream().map(DocumentDto::from).toList();
    }

    /** 이 시각보다 나중에 올라온 문서만 살아 있다. 화면·검색·청소가 같은 기준을 쓴다. */
    private LocalDateTime aliveSince() {
        return LocalDateTime.now().minusMinutes(ttlMinutes);
    }

    /**
     * 검색 범위로 쓸 소유자를 정한다. 목록(listDocuments)과 같은 규칙이어야 한다 —
     * 화면에 보이는 문서와 실제로 검색되는 문서가 다르면 사용자는 버그로 느낀다.
     *
     * @param sessionId 익명 세션 id. 없으면 null
     * @return 내 문서가 있으면 세션 id, 없으면 null (= 예시 문서를 검색한다는 뜻)
     */
    public String resolveSearchOwner(String sessionId) {
        if (sessionId == null || !documentRepository.existsByOwnerAndUploadedAtAfter(sessionId, aliveSince())) {
            return null;
        }
        return sessionId;
    }

    /**
     * 이 세션의 다른 문서를 모두 지운다 (세션당 1개 규칙).
     *
     * 지우는 시점이 중요하다. 새 문서를 저장하기 전에 지우면,
     * 업로드가 중간에 실패했을 때 사용자는 있던 문서마저 잃는다.
     * 그래서 새 문서가 확실히 저장된 뒤에 지운다 - 잠깐 2개가 공존하는 편이 낫다.
     *
     * @param sessionId 익명 세션 id
     * @param keepDocId 방금 올린 문서 (이건 남긴다)
     */
    private void replaceOlderDocuments(String sessionId, String keepDocId) {
        documentRepository.findAllByOwnerOrderByUploadedAtDesc(sessionId).stream()
                .filter(doc -> !doc.getDocId().equals(keepDocId))
                .forEach(doc -> deleteDocument(doc.getDocId(), sessionId));
    }

    /**
     * 수명이 지난 익명 문서를 치운다.
     *
     * 화면과 검색은 이미 aliveSince() 로 만료 시점에 끊기므로, 이 청소가 최대 10분 늦어도
     * 사용자에게는 보이지 않는다. 여기서 하는 일은 저장 공간 회수다.
     * 예시 문서(owner = null)는 쿼리에서 제외되므로 절대 지워지지 않는다.
     */
    @Scheduled(fixedDelayString = "${document.sweep-interval-ms:600000}", initialDelayString = "60000")
    public void sweepExpiredDocuments() {
        List<Document> expired = documentRepository.findAllByOwnerIsNotNullAndUploadedAtBefore(aliveSince());
        if (expired.isEmpty()) {
            return;
        }
        expired.forEach(doc -> deleteDocument(doc.getDocId(), doc.getOwner()));
        log.info("만료 문서 {}건 정리 (수명 {}분)", expired.size(), ttlMinutes);
    }
    /**

    /**
     * 기록 -> 벡터 순서로 지운다 (업로드의 역순).
     * 중간에 실패하면 "기록 없는 벡터" (잔여 벡터)가 남는데, 이건 기동 시 점검과 /cleanup 으로 잡힌다.
     * 반대 순서면 "벡터 없는 기록"이 남아 감지할 방법이 없다.
     *
     * @param docId 지울 문서 id
     * @param sessionId 요청한 익명 세션 id. 없으면 null
     * @return 삭제 결과 (지움 / 없음 / 예시 문서라 보호됨)
     */
    public DeleteResult deleteDocument(String docId, String sessionId) {
        Document document = documentRepository.findById(docId).orElse(null);
        if (document == null) {
            return DeleteResult.NOT_FOUND;
        }
        if (document.getOwner() == null) {
            return DeleteResult.SAMPLE_PROTECTED;   // 예시 문서는 누구도 지울 수 없다
        }
        if (!document.getOwner().equals(sessionId)) {
            // 남의 문서다. 403 이 아니라 404 를 준다 — 그 id 의 문서가 있다는 사실조차 알려줄 이유가 없다.
            return DeleteResult.NOT_FOUND;
        }

        documentRepository.deleteById(docId);
        try {
            aiServiceClient.deleteVectors(docId);
        } catch (Exception e) {
            log.warn("문서 기록은 삭제했으나 벡터 삭제 실패 -> 잔여 벡터로 남음 (docId={}). "
                    + "POST /api/documents/cleanup 으로 정리하세요", docId, e);
        }
        return DeleteResult.DELETED;
    }

    /**
     * Qdrant에는 있지만 H2에는 없는 doc_id - 업로드 중단 강제 종료로 남은 잔여 벡터.
     */
    public List<String> findLeftoverDocIds() {
        Set<String> known = documentRepository.findAll().stream()
                .map(Document::getDocId)
                .collect(Collectors.toSet());

        return aiServiceClient.listDocIds().stream()
                .filter(docId -> !known.contains(docId))
                .toList();
    }

    /**
     * 잔여 벡터를 실제로 삭제한다. 되돌릴 수 없으므로 자동 실행하지 않고
     * 명시적인 요청이 있을 때만 호출한다.
     */
    public int cleanupLeftovers() {
        List<String> leftovers = findLeftoverDocIds();
        for (String docId : leftovers) {
            aiServiceClient.deleteVectors(docId);
            log.warn("잔여 벡터 삭제 (docId={})", docId);
        }
        log.info("잔여 벡터 정리 완료 - {}건", leftovers.size());
        return leftovers.size();
    }

    /**
     * 앱이 완전히 뜬 직후 정합성을 점검하고 경고만 남긴다.
     * 삭제는 하지 않는다 - 사람이 확인하고 결정
     */
    @EventListener(ApplicationReadyEvent.class)
    public void checkLeftoversOnStartup() {
        try {
            List<String> leftovers = findLeftoverDocIds();
            if (leftovers.isEmpty()) {
                log.info("정합성 점검 OK - 잔여 벡터 없음");
            } else {
                log.warn("잔여 벡터 {}건 발견 - 정리하려면 POST /api/documents/cleanup {}" , leftovers.size(), leftovers);
            }
        } catch (Exception e) {
            log.warn("정합성 점검 건너뜀 (AI 서비스 미기동?) - {}", e.getMessage());
        }
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private void cleanupLeftoverVectors(String docId) {
        try {
            aiServiceClient.deleteVectors(docId);
            log.warn("업로드 실패 → 잔여 벡터 정리 완료 (docId={})", docId);
        } catch (Exception cleanupError) {
            log.error("잔여 벡터 정리 실패 (docId={})", docId, cleanupError);
        }
    }

    private void validateExtension(String filename) {
        if (filename == null) throw new InvalidUploadException("파일명이 없습니다.");
        String lower = filename.toLowerCase();
        boolean allowed = Arrays.stream(allowedExtensions.split(","))
                .anyMatch(lower::endsWith);
        if (!allowed) throw new InvalidUploadException("PDF, TXT, MD 파일만 지원합니다.");
    }

    private String extractText(MultipartFile file) throws IOException {
        String filename = file.getOriginalFilename() != null ? file.getOriginalFilename().toLowerCase() : "";
        if (filename.endsWith(".pdf")) {
            try (PDDocument doc = Loader.loadPDF(file.getBytes())) {
                PDFTextStripper stripper = new PDFTextStripper();
                // 다단(컬럼) 레이아웃 PDF에서 텍스트가 좌→우, 상→하 순서로 읽히도록.
                // true/false 를 평가셋 18문항으로 끝까지 비교한 결과 true 가 명확히 우세하다.
                //   Recall@4  94.4% vs 77.8%  /  MRR@4 0.815 vs 0.634
                //   답변 정확도 13/18 vs 8/18  /  과잉 거절 2 vs 5
                // false 에서는 틀린 숫자를 자신 있게 답하는 사례도 나왔다(50cm 를 15cm 로).
                // 추출된 텍스트가 사람 눈에 읽기 좋은 것과 검색·LLM 이 다루기 좋은 것은 다르다.
                stripper.setSortByPosition(true);
                return stripper.getText(doc);
            }
        }
        return new String(file.getBytes(), java.nio.charset.StandardCharsets.UTF_8);
    }

    /**
     * 텍스트를 chunkSize 크기로 분할.
     *
     * 1) 줄 단위로 먼저 쪼갠 뒤 chunkSize 를 넘지 않게 이어붙인다 → 문장·줄이
     *    중간에서 잘리지 않는다 (이력서·표처럼 줄 구조가 의미를 갖는 문서에 중요).
     * 2) 한 줄이 chunkSize 보다 길면 그 줄만 문자 단위로 강제 분할한다.
     * 3) 청크 사이에 chunkOverlap 문자를 겹쳐 문맥 단절을 줄인다.
     */
    static List<String> splitText(String text, int chunkSize, int chunkOverlap) {
        String normalized = text.replace("\r\n", "\n").replace('\r', '\n');
        List<String> chunks = new ArrayList<>();
        StringBuilder cur = new StringBuilder();

        for (String line : normalized.split("\n")) {
            line = line.strip();
            if (line.isEmpty()) continue;

            if (line.length() > chunkSize) {
                if (cur.length() > 0) { chunks.add(cur.toString()); cur.setLength(0); }
                for (int i = 0; i < line.length(); i += chunkSize) {
                    chunks.add(line.substring(i, Math.min(i + chunkSize, line.length())));
                }
                continue;
            }

            if (cur.length() + line.length() + 1 > chunkSize && cur.length() > 0) {
                chunks.add(cur.toString());
                String prev = cur.toString();
                cur.setLength(0);
                if (chunkOverlap > 0 && prev.length() > chunkOverlap && chunkOverlap + line.length() + 1 <= chunkSize) {
                    cur.append(prev, prev.length() - chunkOverlap, prev.length()).append('\n');
                }
            }
            cur.append(line).append('\n');
        }
        if (cur.length() > 0) chunks.add(cur.toString());

        return chunks.stream().map(String::strip).filter(c -> !c.isBlank()).toList();
    }

    private void sendEvent(SseEmitter emitter, Map<String, Object> data) throws IOException {
        emitter.send(SseEmitter.event().data(objectMapper.writeValueAsString(data)));
    }

    private void sendEventQuietly(SseEmitter emitter, Map<String, Object> data) {
        try { sendEvent(emitter, data); } catch (Exception ignored) {}
    }
}
