package com.ragsearch.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.fail;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;
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


    /**
     * 옛 문서가 2개 쌓여 있으면 업로드 한 번에 둘 다 지운다.
     *
     * 왜 업로드를 세 번 하는 방식으로는 이걸 잡을 수 없나: 제한이 정상이면 옛 문서는
     * 항상 정확히 1개다. 그래서 "하나만 지우는" 구현으로 바뀌어도 업로드 3연속은 그냥 통과한다
     * (2026-09-29 에 .limit(1) 을 주입해 실제로 확인했다 - 세 테스트 모두 통과했다).
     * 2개가 쌓인 상태는 업로드로 만들 수 없으므로 리포지토리에 직접 심는다.
     *
     * 이 경로가 실제로 중요한 이유: 평가 하네스가 한 세션에 문서를 여러 개 올리려 했다가
     * 이 규칙에 조용히 지워졌다. 코드는 멀쩡한데 지표만 무너지는 실패였고, 화면에 안 보이는
     * 경로라 아무도 알려주지 않았다. 하네스는 문서마다 세션을 따로 쓰도록 고쳤다 -
     * 운영이 세션당 1개이므로 평가도 그래야 한다.
     */
    @Test
    void uploadRemovesEveryOlderDocumentNotJustOne() {
        // 어떤 이유로든 한 세션에 문서가 2개 쌓인 상태를 만든다.
        String oldA = seedDocument("옛문서A.txt", LocalDateTime.now().minusMinutes(3));
        String oldB = seedDocument("옛문서B.txt", LocalDateTime.now().minusMinutes(2));
        assertThat(myDocuments()).hasSize(2);

        documentService.upload(textFile("새문서.txt"), SESSION);
        waitUntil(() -> {
            List<Document> mine = myDocuments();
            return mine.size() == 1 && "새문서.txt".equals(mine.get(0).getFilename());
        }, "옛 문서 2개가 모두 교체");

        assertThat(documentRepository.existsById(oldA)).isFalse();
        assertThat(documentRepository.existsById(oldB)).isFalse();
        // 기록만 지우면 잔여 벡터가 남는다 - 둘 다 벡터까지 지웠는지 본다.
        verify(aiServiceClient).deleteVectors(oldA);
        verify(aiServiceClient).deleteVectors(oldB);
    }

    /** 업로드 경로를 타지 않고 문서 기록만 만든다. 업로드로는 만들 수 없는 상태를 세팅할 때 쓴다. */
    private String seedDocument(String filename, LocalDateTime uploadedAt) {
        String docId = UUID.randomUUID().toString();
        documentRepository.save(Document.builder()
                .docId(docId)
                .filename(filename)
                .chunkCount(1)
                .uploadedAt(uploadedAt)
                .owner(SESSION)
                .build());
        return docId;
    }
}