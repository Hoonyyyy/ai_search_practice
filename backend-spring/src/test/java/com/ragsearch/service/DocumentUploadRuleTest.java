package com.ragsearch.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.fail;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.function.BooleanSupplier;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import com.ragsearch.client.AiServiceClient;
import com.ragsearch.domain.Document;
import com.ragsearch.repository.DocumentRepository;

/**
 * 업로드 경로의 규칙 두 가지를 고정한다.
 *
 * 1. 세션 없는 업로드는 거절된다 - 허용하면 owner 가 NULL 로 저장돼
 *      "아무도 지울 수 없는 예시 문서" 가 하나 늘어난다
 * 2. 새로 올리면 옛 문서가 교체된다 (세션당 1개)
 *
 * 업로드는 별도 스레드에서 끝나므로 결과를 기다려야 한다. 그래서 이 파일에만 wiatUntil 이 있다.
 */

@SpringBootTest(properties = {
        "spring.datasource.url=jdbc:h2:mem:ragsearchtest",
        "spring.jpa.hibernate.ddl-auto=create-drop",

})
class DocumentUploadRuleTest {

    private static final String SESSION = "test-session";

    @Autowired
    private DocumentService documentService;

    @Autowired
    private DocumentRepository documentRepository;

    @MockBean
    private AiServiceClient aiServiceClient;

    @BeforeEach
    void clearDocuments() {
        documentRepository.deleteAll();
    }

    private MultipartFile textFile(String filename) {
        return new MockMultipartFile("file", filename, "text/plain",
                    "사내 규정 문서입니다. 테스트용 내용이 들어 있습니다.".getBytes(StandardCharsets.UTF_8));
    }

    private List<Document> myDocuments() {
        return documentRepository.findAllByOwnerOrderByUploadedAtDesc(SESSION);
    }

    /** 업로드는 다른 스레드에서 끝난다. 조건이 만족될 때까지 최대 10초 기다린다. */
    private void waitUntil(BooleanSupplier condition, String description) {
        long deadline = System.currentTimeMillis() + 10_000;
        while (System.currentTimeMillis() < deadline) {
            if (condition.getAsBoolean()) {
                return ;
            }
            try {
                Thread.sleep(50);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
        fail("10초 안에 이뤄지지 않았습니다: " + description
                + "\n  현재 내 문서: " + myDocuments().stream().map(Document::getFilename).toList());

    }

    @Test
    void uploadWithoutSessionStoresNothing() {
        documentService.upload(textFile("내문서.txt"), null);

        // 세션이 없으면 스레드에 넘기기도 전에 거절한다 - 그래서 여기선 기다릴 필요가 없다
        assertThat(documentRepository.count()).isZero();
        verifyNoInteractions(aiServiceClient);
    }

    @Test
    void uploadingAgainReplacesTheOlderDocument() {
        documentService.upload(textFile("첫번째.txt"), SESSION);
        waitUntil(() -> myDocuments().size() == 1, "첫 문서 저장");
        String firstDocId = myDocuments().get(0).getDocId();

        documentService.upload(textFile(("두번째.txt")), SESSION);
        //새 문서를 저장한 뒤에 옛 문서를 지우므로, 잠깐 2개가 공존할 수 있다
        waitUntil(() -> {
            List<Document> mine = myDocuments();      // 한 번만 묻는다
            return mine.size() == 1 && "두번째.txt".equals(mine.get(0).getFilename());
        }, "옛 문서 교체");


        assertThat(documentRepository.existsById(firstDocId)).isFalse();
        verify(aiServiceClient).deleteVectors(firstDocId);  // 벡터도 같이 지웠는가
    }

}