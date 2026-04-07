package com.ragsearch.service;

import com.ragsearch.dto.metrics.MetricsSummaryDto;
import com.ragsearch.dto.metrics.QueryLogDto;
import com.ragsearch.dto.metrics.TimelinePointDto;
import com.ragsearch.repository.QueryLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class MetricsService {

    private final QueryLogRepository queryLogRepository;

    public MetricsSummaryDto getSummary() {
        return new MetricsSummaryDto(
                queryLogRepository.countAll(),
                Math.round(queryLogRepository.avgResponseTimeMs() * 10.0) / 10.0,
                queryLogRepository.sumTotalTokens(),
                queryLogRepository.avgUserScore()
        );
    }

    /** 최신 100건을 시간 오름차순으로 반환 (차트용) */
    public List<TimelinePointDto> getTimeline(int limit) {
        return queryLogRepository.findTop100ByOrderByTimestampDesc()
                .stream()
                .limit(limit)
                .sorted((a, b) -> a.getTimestamp().compareTo(b.getTimestamp()))
                .map(TimelinePointDto::from)
                .toList();
    }

    public List<QueryLogDto> getRecentLogs(int limit) {
        return queryLogRepository.findTop100ByOrderByTimestampDesc()
                .stream()
                .limit(limit)
                .map(QueryLogDto::from)
                .toList();
    }
}
