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

    @Builder
    public Document(String docId, String filename, int chunkCount, LocalDateTime uploadedAt) {
        this.docId = docId;
        this.filename = filename;
        this.chunkCount = chunkCount;
        this.uploadedAt = uploadedAt;
    }
}
