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

    /**
     * 최근 질문 목록. 통계와 달리 자기 질문만 보여준다.
     * 무엇을 물었는지는 그 방문자의 것이고, 문서를 올린 사람이라면 더욱 그렇다.
     *
     * 세션이 없으면 빈 목록을 준다 - 남의 질문을 대신 보여주느니 비어 있는 편이 낫다고 판단함
     *
     * @param limit 최대 개수
     * @param sessionId 익명 세션 id. 없으면 null
     * @return 이 세션의 최근 질문 목록
     */
    public List<QueryLogDto> getRecentLogs(int limit, String sessionId) {
        if (sessionId == null || sessionId.isBlank()) {
            return List.of();
        }
        return queryLogRepository.findTop100ByOwnerOrderByTimestampDesc(sessionId)
                .stream()
                .limit(limit)
                .map(QueryLogDto::from)
                .toList();
    }
}
