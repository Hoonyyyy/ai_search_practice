package com.ragsearch.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.LocalDateTime;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.junit.jupiter.api.Test;

import com.ragsearch.client.AiServiceClient;
import com.ragsearch.domain.Document;
import com.ragsearch.dto.document.DocumentDto;
import com.ragsearch.repository.DocumentRepository;

/**
 * 문서 수명(ttl-minutes) 규칙을 고정한다.
 *
 * 2026-09-23 에 실제로 깨졌던 자리, 검색(resolveSearchOwner)은 만료를 반영했는데
 * 목록(listDocuments)만 빠져서, "목록에는 있는데 검색은 안 되는" 상태가 됐다.
 * 사용자 입장에선 "문서를 올렸는데 그 내용을 못 찾는" 가장 헷갈리는 증상이다.
 *
 * 손으로 확인하려면 1시간을 기다려야 한다. 여기서는 uploadedAt 을 과거로 박아서
 * 기다리지 않고 만료 상태를 만든다 - 이 테스트 존재 이유
 */

@SpringBootTest(properties = {
        // 실제 로컬 DB(./data/ragsearch)를 건드리지 않도록 메모리 DB 로 바꾼다
        // 테스트 클래스끼리 이 설정이 "똑같아야" Spring 이 앱을 한 번만 띄우고 재사용한다
        "spring.datasource.url=jdbc:h2:mem:ragsearchtest",
        "spring.jpa.hibernate.ddl-auto=create-drop",
})
public class DocumentExpiryTest {

    private static final String SESSION = "test-session";
    private static final String OTHER_SESSION = "other-session";

    @Autowired
    private DocumentService documentService;

    @Autowired
    private DocumentRepository documentRepository;

    /** FastAPI 호출을 가짜로 바꾼다 - 테스트가 파이썬 서버나 OpenAI를 필요로 하면 안 된다 */
    @MockBean
    private AiServiceClient aiServiceClient;

    @BeforeEach
    void clearDocuments() {
        documentRepository.deleteAll();;
    }

    private void saveDocument(String docId, String filename, String owner, LocalDateTime uploadedAt) {
        documentRepository.save(Document.builder()
                .docId(docId)
                .filename(filename)
                .chunkCount(1)
                .uploadedAt(uploadedAt)
                .owner(owner)
                .build());
    }

    @Test
    void expiredDocumentDisappearsAndSampleTakesOver() {
        saveDocument("sample", "Galaxybook_guide.pdf", null, LocalDateTime.now().minusDays(3));
        saveDocument("mine", "내문서.txt", SESSION, LocalDateTime.now().minusMinutes(61));

        List<DocumentDto> visible = documentService.listDocuments(SESSION);

        assertThat(visible).hasSize(1);
        assertThat(visible.get(0).getFilename()).isEqualTo("Galaxybook_guide.pdf");
        assertThat(visible.get(0).isSample()).isTrue();
    }

    @Test
    void expiredDocumentIsAlsoOutOfSearchScope() {
        saveDocument("sample", "Galaxybook_guide.pdf", null, LocalDateTime.now().minusDays(3));
        saveDocument("mine", "내문서.txt", SESSION, LocalDateTime.now().minusMinutes(61));

        // null = "예시 문서를 검색한다" 는 뜻
        assertThat(documentService.resolveSearchOwner(SESSION)).isNull();
    }

    @Test
    void livingDocumentAppearsInBothListAndSearch() {
        saveDocument("sample", "Galaxybook_guide.pdf", null, LocalDateTime.now().minusDays(3));
        saveDocument("mine", "내문서.txt", SESSION, LocalDateTime.now().minusMinutes(59));

        List<DocumentDto> visible = documentService.listDocuments(SESSION);

        assertThat(visible).hasSize(1);
        assertThat(visible.get(0).getFilename()).isEqualTo("내문서.txt");
        assertThat(visible.get(0).isSample()).isFalse();
        assertThat(documentService.resolveSearchOwner(SESSION)).isEqualTo(SESSION);
    }

    @Test
    void sampleIsNeverExpired() {
        // 3일 전에 올라간 예시 문서도 여전히 보여야 한다 (owner가 없으면 수명이 없다)
        saveDocument("sample", "Galaxybook_guide.pdf", null, LocalDateTime.now().minusDays(3));

        assertThat(documentService.listDocuments(OTHER_SESSION)).hasSize(1);
    }
}
