import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TimelinePoint } from '../../../types';
import chartStyles from './Chart.module.css';

interface Props { data: TimelinePoint[] }

const formatTime = (v: string) =>
  new Date(v + 'Z').toLocaleTimeString('ko-KR', { timeZone: 'Asia/Seoul', hour: '2-digit', minute: '2-digit', hour12: false });

const ResponseTimeChart: React.FC<Props> = ({ data }) => (
  <div className={chartStyles.card}>
    <div className={chartStyles.title}>응답시간 추이 (ms)</div>
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
        <XAxis dataKey="timestamp" tickFormatter={formatTime} tick={{ fill: '#666', fontSize: 11 }} />
        <YAxis tick={{ fill: '#666', fontSize: 11 }} />
        <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #444', borderRadius: 8 }} labelStyle={{ color: '#aaa' }} itemStyle={{ color: '#10b981' }} />
        <Line type="monotone" dataKey="response_time_ms" stroke="#10b981" dot={false} strokeWidth={2} name="응답시간(ms)" />
      </LineChart>
    </ResponsiveContainer>
  </div>
);

export default ResponseTimeChart;
