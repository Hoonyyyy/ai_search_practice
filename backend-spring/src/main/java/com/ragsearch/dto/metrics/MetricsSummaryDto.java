package com.ragsearch.dto.metrics;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class MetricsSummaryDto {
    private final long totalQueries;
    private final double avgResponseTimeMs;
    private final long totalTokensUsed;
    private final Double avgUserScore;
}
