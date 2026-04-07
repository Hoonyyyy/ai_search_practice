package com.ragsearch.controller;

import com.ragsearch.dto.metrics.MetricsSummaryDto;
import com.ragsearch.dto.metrics.QueryLogDto;
import com.ragsearch.dto.metrics.TimelinePointDto;
import com.ragsearch.service.MetricsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/metrics")
@RequiredArgsConstructor
public class MetricsController {

    private final MetricsService metricsService;

    @GetMapping("/summary")
    public MetricsSummaryDto summary() {
        return metricsService.getSummary();
    }

    @GetMapping("/timeline")
    public List<TimelinePointDto> timeline(@RequestParam(defaultValue = "50") int limit) {
        return metricsService.getTimeline(limit);
    }

    @GetMapping("/recent")
    public List<QueryLogDto> recent(@RequestParam(defaultValue = "20") int limit) {
        return metricsService.getRecentLogs(limit);
    }
}
