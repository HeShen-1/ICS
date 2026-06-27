import { request } from './client';

export interface StatsOverview {
  total_users: number;
  total_sessions: number;
  total_messages: number;
  total_documents: number;
  feedback_positive_count: number;
  feedback_negative_count: number;
}

export interface DailyTrendItem {
  date: string;
  count: number;
}

export interface FeedbackSession {
  session_id: number;
  title: string;
  positive_count: number;
  negative_count: number;
}

export function getStatsOverview(): Promise<StatsOverview> {
  return request('/stats/overview');
}

export function getDailyTrend(days: number = 7): Promise<DailyTrendItem[]> {
  return request(`/stats/daily_trend?days=${days}`);
}

export function getFeedbackSessions(): Promise<FeedbackSession[]> {
  return request('/stats/feedback_sessions');
}
