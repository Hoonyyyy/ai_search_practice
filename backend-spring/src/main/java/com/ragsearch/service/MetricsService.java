package com.ragsearch.service;

import com.ragsearch.domain.QueryLog;
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

    /**
     * 평균 응답시간은 전체가 아니라 최근 이만큼만 본다.
     * 전체 평균은 IPv6 문제를 고치기 전 기록(4,485ms 시절)과 콜드 스타트까지 섞여 있어
     * 지금 상태를 나타내지 못한다. 숨길 게 아니라 숫자를 의미 있게 만든다.
     */
    private static final int RECENT_WINDOW = 20;

    public MetricsSummaryDto getSummary() {
        int[] recentMs = queryLogRepository.findTop100ByOrderByTimestampDesc()
                .stream()
                .limit(RECENT_WINDOW)
                .mapToInt(QueryLog::getResponseTimeMs)
                .sorted()
                .toArray();

        return new MetricsSummaryDto(
                queryLogRepository.countAll(),
                median(recentMs),
                queryLogRepository.sumTotalTokens()
        );
    }

    /** 정렬된 배열의 중앙값. 빈 배열이면 0. */
    private static double median(int[] sorted) {
        if (sorted.length == 0) {
            return 0;
        }
        int mid = sorted.length / 2;
        return sorted.length % 2 == 1
                ? sorted[mid]
                : (sorted[mid - 1] + sorted[mid]) / 2.0;
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
