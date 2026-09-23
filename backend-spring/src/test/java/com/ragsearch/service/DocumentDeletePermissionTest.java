package com.ragsearch.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.verify;

import java.time.LocalDateTime;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;

import com.ragsearch.client.AiServiceClient;
import com.ragsearch.domain.Document;
import com.ragsearch.dto.document.DocumentDto;
import com.ragsearch.repository.DocumentRepository;
import com.ragsearch.service.DocumentService.DeleteResult;

/**
 * 문서를 누가 지울 수 있는지 고정한다.
 *
 * 삭제 결과는 세 가지다 - 지움(DELETED) / 없음(NOT_FOUND) / 예시라 보호됨(SAMPLE_PROTECTED).
 * 상태 코드는 화면에 안 보이기 때문에 손으로 확인하려면 매번 개발자 도구를 열어야 한다.
 *
 * 남의 문서에 403 이 아니라 404 를 주는 것도 여기서 못 박는다.
 * 403은 "권한이 없다" 이고, 그건 곧 "그 id의 문서가 존재한다"는 정보를 흘리는 것이다.
*/

@SpringBootTest(properties = {
    "spring.datasource.url=jdbc:h2:mem:ragsearchtest",
    "spring.jpa.hibernate.ddl-auto=create-drop",
})
class DocumentDeletePermissionTest {

    private static final String SESSION = "test-session";
    private static final String OTHER_SESSION = "other-session";

    @Autowired
    private DocumentService documentService;

    @Autowired
    private DocumentRepository documentRepository;

    @MockBean
    private AiServiceClient aiServiceClient;

    @BeforeEach
    void clearDocuments() {
        documentRepository.deleteAll();;
    }

    private void saveDocument(String docId, String filename, String owner) {
        documentRepository.save(Document.builder()
                .docId(docId)
                .filename(filename)
                .chunkCount(1)
                .uploadedAt(LocalDateTime.now())
                .owner(owner)
                .build());
    }

    @Test
    void otherSessionSeesSampleNotMyDocument() {
        saveDocument("sample", "Galaxybook_guide.pdf", null);
        saveDocument("mine", "내문서.txt", SESSION);

        List<DocumentDto> visible = documentService.listDocuments(OTHER_SESSION);

        assertThat(visible).hasSize(1);
        assertThat(visible.get(0).getFilename()).isEqualTo("Galaxybook_guide.pdf");
    }

    @Test
    void ownerCanDeleteOwnDocument() {
        saveDocument("mine", "내문서.txt", SESSION);

        DeleteResult result = documentService.deleteDocument("mine", SESSION);

        assertThat(result).isEqualTo(DeleteResult.DELETED);
        assertThat(documentRepository.existsById("mine")).isFalse();
        verify(aiServiceClient).deleteVectors("mine");  // 벡터 삭제까지 요청했는가
    }

    @Test
    void deletingSomeoneElsesDocumentReturnsNotFound() {
        saveDocument("mine", "내문서.txt", SESSION);

        DeleteResult result = documentService.deleteDocument("mine", OTHER_SESSION);

        assertThat(result).isEqualTo(DeleteResult.NOT_FOUND);
        assertThat(documentRepository.existsById("mine")).isTrue(); // 실제로 살아 있어야 한다
    }

    @Test
    void sampleDocumentCannotBeDeletedByAnyone() {
        saveDocument("sample", "Galaxybook_guide.pdf", null);

        DeleteResult result = documentService.deleteDocument("sample", SESSION);

        assertThat(result).isEqualTo(DeleteResult.SAMPLE_PROTECTED);
        assertThat(documentRepository.existsById("sample")).isTrue();
    }

    @Test
    void deletingUnknownDocumentReturnsNotFound() {
        assertThat(documentService.deleteDocument("no-such-id", SESSION))
                .isEqualTo(DeleteResult.NOT_FOUND);
    }
}