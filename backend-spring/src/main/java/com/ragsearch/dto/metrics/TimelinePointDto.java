package com.ragsearch.dto.metrics;

import com.ragsearch.domain.QueryLog;
import lombok.Getter;

import java.time.format.DateTimeFormatter;

@Getter
public class TimelinePointDto {
    private final String timestamp;
    private final int responseTimeMs;
    private final int totalTokens;

    private TimelinePointDto(QueryLog log) {
        this.timestamp = log.getTimestamp().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        this.responseTimeMs = log.getResponseTimeMs();
        this.totalTokens = log.getTotalTokens();
    }

    public static TimelinePointDto from(QueryLog log) {
        return new TimelinePointDto(log);
    }
}
