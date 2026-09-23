package com.ragsearch.domain;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

/**
 * 검색 쿼리 로그 엔티티.
 * 매 검색마다 질문/답변/성능 지표/사용자 평가를 기록한다.
 */
@Entity
@Table(name = "query_logs")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@ToString
public class QueryLog {

    @Id
    private String id;

    @Column(nullable = false)
    private LocalDateTime timestamp;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String question;

    @Column(columnDefinition = "TEXT")
    private String answer;

    @Column(name = "response_time_ms")
    private int responseTimeMs;

    @Column(name = "input_tokens")
    private int inputTokens;

    @Column(name = "output_tokens")
    private int outputTokens;

    @Column(name = "total_tokens")
    private int totalTokens;

    @Column(name = "retrieved_chunks")
    private int retrievedChunks;


    /**
     * 이 질문을 던진 익명 세션 id (문서의 owner 와 같은 값).
     * 통계는 전부 합쳐서 보여주지만, 질문 내용은 자기 것만 보이게 하려고 남긴다.
     */
    @Column(name = "owner")
    private String owner;

    @Builder
    public QueryLog(String id, LocalDateTime timestamp, String question, String answer,
                    int responseTimeMs, int inputTokens, int outputTokens,
                    int totalTokens, int retrievedChunks, String owner) {
        this.id = id;
        this.timestamp = timestamp;
        this.question = question;
        this.answer = answer;
        this.responseTimeMs = responseTimeMs;
        this.inputTokens = inputTokens;
        this.outputTokens = outputTokens;
        this.totalTokens = totalTokens;
        this.retrievedChunks = retrievedChunks;
        this.owner = owner;
    }

}
