package com.ragsearch.repository;

import com.ragsearch.domain.QueryLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface QueryLogRepository extends JpaRepository<QueryLog, String> {

    List<QueryLog> findTop100ByOrderByTimestampDesc();

    @Query("SELECT COUNT(q) FROM QueryLog q")
    long countAll();

    @Query("SELECT COALESCE(AVG(q.responseTimeMs), 0) FROM QueryLog q")
    double avgResponseTimeMs();

    @Query("SELECT COALESCE(SUM(q.totalTokens), 0) FROM QueryLog q")
    long sumTotalTokens();

    @Query("SELECT AVG(q.userScore) FROM QueryLog q WHERE q.userScore IS NOT NULL")
    Double avgUserScore();
}
