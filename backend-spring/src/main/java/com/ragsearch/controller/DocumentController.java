package com.ragsearch.controller;

import com.ragsearch.dto.document.DocumentDto;
import com.ragsearch.service.DocumentService;
import com.ragsearch.service.DocumentService.DeleteResult;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/documents")
@RequiredArgsConstructor
public class DocumentController {

    private final DocumentService documentService;

    @PostMapping(value = "/upload", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter upload(@RequestParam("file") MultipartFile file,
                             @RequestHeader(value = "X-Session-Id", required = false) String sessionId,
                             HttpServletResponse response) {
        response.setHeader("X-Accel-Buffering", "no");
        response.setHeader("Cache-Control", "no-cache");
        return documentService.upload(file, sessionId);
    }

    @GetMapping
    public List<DocumentDto> listDocuments(
            @RequestHeader(value = "X-Session-Id", required = false) String sessionId) {
        return documentService.listDocuments(sessionId);
    }

    @DeleteMapping("/{docId}")
    public ResponseEntity<Map<String, String>> deleteDocument(
            @PathVariable String docId,
            @RequestHeader(value = "X-Session-Id", required = false) String sessionId) {
        return switch (documentService.deleteDocument(docId, sessionId)) {
            case DELETED -> ResponseEntity.ok(Map.of("message", "삭제 완료"));
            case SAMPLE_PROTECTED -> ResponseEntity.status(HttpStatus.FORBIDDEN)
                    .body(Map.of("message", "예시 문서는 삭제할 수 없습니다."));
            case NOT_FOUND -> ResponseEntity.status(HttpStatus.NOT_FOUND)
                    .body(Map.of("message", "문서를 찾을 수 없습니다."));
        };
    }

    /** 잔여 벡터 조회 - 삭제하지 않고 보기만 한다 */
    @GetMapping("/leftovers")
    public Map<String, Object> leftovers() {
        List<String> docIds = documentService.findLeftoverDocIds();
        return Map.of("count", docIds.size(), "doc_ids", docIds);
    }

    /** 잔여 벡터 정리 - 되돌릴 수 없으므로 명시적 요청으로만 실행. */
    @PostMapping("/cleanup")
    public ResponseEntity<Map<String, Object>> cleanupLeftovers() {
        int deleted = documentService.cleanupLeftovers();
        return ResponseEntity.ok(Map.of("deleted", deleted));
    }
}
