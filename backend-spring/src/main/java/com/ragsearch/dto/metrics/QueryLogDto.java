package com.ragsearch.dto.metrics;

import com.ragsearch.domain.QueryLog;
import lombok.Getter;

import java.time.format.DateTimeFormatter;

@Getter
public class QueryLogDto {
    private final String id;
    private final String timestamp;
    private final String question;
    private final String answer;
    private final int responseTimeMs;
    private final int totalTokens;
    private final Double userScore;

    private QueryLogDto(QueryLog log) {
        this.id = log.getId();
        this.timestamp = log.getTimestamp().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        this.question = log.getQuestion();
        this.answer = log.getAnswer();
        this.responseTimeMs = log.getResponseTimeMs();
        this.totalTokens = log.getTotalTokens();
        this.userScore = log.getUserScore();
    }

    public static QueryLogDto from(QueryLog log) {
        return new QueryLogDto(log);
    }
}
