import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TimelinePoint } from '../../../types';
import chartStyles from './Chart.module.css';

interface Props { data: TimelinePoint[] }

const formatTime = (v: string) =>
  new Date(v + 'Z').toLocaleTimeString('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false });

const TokenUsageChart: React.FC<Props> = ({ data }) => (
  <div className={chartStyles.card}>
    <div className={chartStyles.title}>토큰 사용량 추이</div>
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="timestamp" tickFormatter={formatTime} tick={{ fill: '#666', fontSize: 11 }} />
        <YAxis tick={{ fill: '#666', fontSize: 11 }} />
        <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #444', borderRadius: 8 }} labelStyle={{ color: '#aaa' }} itemStyle={{ color: '#f59e0b' }} />
        <Bar dataKey="total_tokens" fill="#f59e0b" radius={[4, 4, 0, 0]} name="총 토큰" />
      </BarChart>
    </ResponsiveContainer>
  </div>
);

export default TokenUsageChart;
