import React, { useEffect, useState } from 'react';
import StatCard from './StatCard';
import ResponseTimeChart from './charts/ResponseTimeChart';
import TokenUsageChart from './charts/TokenUsageChart';
import ScoreChart from './charts/ScoreChart';
import { getMetricsSummary, getTimeline, getRecentLogs } from '../../api/metrics';
import { MetricsSummary, TimelinePoint, QueryLog } from '../../types';
import styles from './MetricsDashboard.module.css';

const PAGE_SIZE = 10;

const toKST = (utcStr: string) =>
  new Date(utcStr + 'Z').toLocaleString('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false,
  });

const MetricsDashboard: React.FC = () => {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [logs, setLogs] = useState<QueryLog[]>([]);
  const [page, setPage] = useState(1);

  const load = async () => {
    const [s, t, l] = await Promise.all([getMetricsSummary(), getTimeline(), getRecentLogs(100)]);
    setSummary(s);
    setTimeline(t);
    setLogs(l);
    setPage(1);
  };

  useEffect(() => { load(); }, []);

  const totalPages = Math.max(1, Math.ceil(logs.length / PAGE_SIZE));
  const pagedLogs = logs.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className={styles.container}>
      <div className={styles.topRow}>
        <h2 className={styles.title}>성능 대시보드</h2>
        <button className={styles.refreshBtn} onClick={load}>새로고침</button>
      </div>

      {summary && (
        <div className={styles.statRow}>
          <StatCard label="총 쿼리 수" value={summary.total_queries.toLocaleString()} color="#6366f1" />
          <StatCard label="평균 응답시간" value={`${summary.avg_response_time_ms}ms`} color="#10b981" />
          <StatCard label="총 토큰 사용" value={summary.total_tokens_used.toLocaleString()} color="#f59e0b" sub="tokens" />
          <StatCard label="평균 평가 점수" value={summary.avg_user_score ? `${summary.avg_user_score} / 5` : '-'} color="#a78bfa" />
        </div>
      )}

      <ResponseTimeChart data={timeline} />
      <TokenUsageChart data={timeline} />
      <ScoreChart data={timeline} />

      {logs.length > 0 && (
        <div>
          <div className={styles.logHeader}>
            <h3 className={styles.logTitle}>
              쿼리 로그 <span className={styles.logCount}>({logs.length}건)</span>
            </h3>
            <div className={styles.pagination}>
              <button className={styles.pageBtn} onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>이전</button>
              <span className={styles.pageInfo}>{page} / {totalPages}</span>
              <button className={styles.pageBtn} onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}>다음</button>
            </div>
          </div>
          <div className={styles.logList}>
            {pagedLogs.map((log) => (
              <div key={log.id} className={styles.logItem}>
                <div className={styles.logItemTop}>
                  <span className={styles.logQuestion}>
                    {log.question.length > 60 ? log.question.slice(0, 60) + '...' : log.question}
                  </span>
                  <span className={styles.logTime}>{toKST(log.timestamp)}</span>
                </div>
                <div className={styles.logMeta}>
                  <span className={styles.logMetaTime}>{log.response_time_ms}ms</span>
                  <span className={styles.logMetaTokens}>{log.total_tokens} tokens</span>
                  {log.user_score && <span className={styles.logMetaScore}>★ {log.user_score}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MetricsDashboard;
