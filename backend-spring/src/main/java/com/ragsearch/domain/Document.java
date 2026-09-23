package com.ragsearch.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

/**
 * 업로드된 문서 메타데이터 엔티티.
 * 벡터 데이터는 Python AI 서비스(ChromaDB)에 저장되고
 * 이 엔티티는 Spring Boot의 H2에서 관리한다.
 */
@Entity
@Table(name = "documents")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@ToString
public class Document {

    @Id
    @Column(name = "doc_id")
    private String docId;

    @Column(nullable = false)
    private String filename;

    @Column(name = "chunk_count")
    private int chunkCount;

    @Column(name = "uploaded_at", nullable = false)
    private LocalDateTime uploadedAt;

    /**
     * 이 문서를 올린 익명 세션 id (브라우저의 X-Session-Id 헤더 값).
     * NULL 이면 어떤 세션에도 속하지 않은 "예시 문서" 다.
     * 인증이 아니라 위조 가능하다 — 방문자끼리 문서가 섞이지 않게 나누는 용도일 뿐이다.
     */
    @Column(name = "owner")
    private String owner;

    @Builder
    public Document(String docId, String filename, int chunkCount, LocalDateTime uploadedAt, String owner) {
        this.docId = docId;
        this.filename = filename;
        this.chunkCount = chunkCount;
        this.uploadedAt = uploadedAt;
        this.owner = owner;
    }
}
