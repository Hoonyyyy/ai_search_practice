import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TimelinePoint } from '../../../types';
import chartStyles from './Chart.module.css';

interface Props { data: TimelinePoint[] }

const formatTime = (v: string) =>
  new Date(v + 'Z').toLocaleTimeString('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false });

const ScoreChart: React.FC<Props> = ({ data }) => {
  const scored = data.filter((d) => d.user_score !== null);
  return (
    <div className={chartStyles.card}>
      <div className={chartStyles.title}>사용자 평가 점수 추이 (1~5)</div>
      {scored.length === 0 ? (
        <div className={chartStyles.empty}>아직 평가 데이터가 없습니다.</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={scored}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="timestamp" tickFormatter={formatTime} tick={{ fill: '#666', fontSize: 11 }} />
            <YAxis domain={[0, 5]} tick={{ fill: '#666', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #444', borderRadius: 8 }} labelStyle={{ color: '#aaa' }} itemStyle={{ color: '#a78bfa' }} />
            <Line type="monotone" dataKey="user_score" stroke="#a78bfa" dot={{ fill: '#a78bfa' }} strokeWidth={2} name="평가 점수" />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};

export default ScoreChart;
