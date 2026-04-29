import { MetricsSummary, TimelinePoint, QueryLog } from '../types';

const BASE = process.env.REACT_APP_API_URL ?? 'http://localhost:8080/api';

export const getMetricsSummary = async (): Promise<MetricsSummary> => {
  const resp = await fetch(`${BASE}/metrics/summary`);
  return resp.json();
};

export const getTimeline = async (limit = 50): Promise<TimelinePoint[]> => {
  const resp = await fetch(`${BASE}/metrics/timeline?limit=${limit}`);
  return resp.json();
};

export const getRecentLogs = async (limit = 20): Promise<QueryLog[]> => {
  const resp = await fetch(`${BASE}/metrics/recent?limit=${limit}`);
  return resp.json();
};
