import React, { useState } from 'react';
import { QueryResponse, SourceChunk } from '../../types';
import { sendFeedback } from '../../api/search';
import styles from './AnswerPanel.module.css';

interface MetricBadge {
  label: string;
  value: string;
  color: string;
  borderColor: string;
}

interface Props {
  streamText: string;
  sources: SourceChunk[];
  result: QueryResponse | null;
  streaming: boolean;
}

const AnswerPanel: React.FC<Props> = ({ streamText, sources, result, streaming }) => {
  const [score, setScore] = useState<number | null>(null);
  const [sent, setSent] = useState(false);

  const hasContent = streamText || streaming;

  if (!hasContent && !result) {
    return <div className={styles.placeholder}>질문을 입력하면 답변이 여기에 표시됩니다.</div>;
  }

  const m = result?.metrics;

  const handleScore = async (s: number) => {
    if (!m?.query_id) return;
    setScore(s);
    await sendFeedback(m.query_id, s);
    setSent(true);
  };

  const badges: MetricBadge[] = m && m.response_time_ms > 0 ? [
    { label: '응답시간', value: `${m.response_time_ms}ms`, color: '#10b981', borderColor: '#10b98144' },
    { label: '총 토큰', value: m.total_tokens.toLocaleString(), color: '#f59e0b', borderColor: '#f59e0b44' },
    { label: '검색 청크', value: `${m.retrieved_chunks}개`, color: '#6366f1', borderColor: '#6366f144' },
  ] : [];

  return (
    <div className={styles.container}>
      {badges.length > 0 && (
        <div className={styles.badges}>
          {badges.map((b) => (
            <div key={b.label} className={styles.badge} style={{ border: `1px solid ${b.borderColor}` }}>
              <span className={styles.badgeLabel}>{b.label} </span>
              <span className={styles.badgeValue} style={{ color: b.color }}>{b.value}</span>
            </div>
          ))}
        </div>
      )}

      <div className={styles.answerBox}>
        <div className={styles.answerLabel}>
          답변 {streaming && <span className={styles.streamingDot}>●</span>}
        </div>
        <div className={styles.answerText}>
          {streamText}
          {streaming && <span className={styles.cursor}>▍</span>}
        </div>
      </div>

      {sources.length > 0 && (
        <div>
          <div className={styles.sourceLabel}>참고 문서 ({sources.length})</div>
          <div className={styles.sourceList}>
            {sources.map((s, i) => (
              <div key={i} className={styles.sourceItem}>
                <div className={styles.sourceFilename}>📄 {s.filename}</div>
                <div className={styles.sourcePreview}>{s.content_preview}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!streaming && streamText && (
        <div className={styles.feedback}>
          <span className={styles.feedbackLabel}>답변이 도움이 됐나요?</span>
          {sent ? (
            <span className={styles.feedbackDone}>감사합니다! ({score}점)</span>
          ) : (
            [1, 2, 3, 4, 5].map((s) => (
              <button
                key={s}
                className={styles.starBtn}
                onClick={() => handleScore(s)}
                style={{ opacity: score && score >= s ? 1 : 0.4 }}
              >★</button>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AnswerPanel;
