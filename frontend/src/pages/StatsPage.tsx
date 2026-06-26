import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStatsOverview, getDailyTrend, type StatsOverview, type DailyTrendItem } from '../api/stats';
import { ArrowLeft, Users, MessageSquare, FileText, MessagesSquare, ThumbsUp, ThumbsDown } from 'lucide-react';

export function StatsPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [trend, setTrend] = useState<DailyTrendItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStatsOverview(), getDailyTrend(7)])
      .then(([ov, tr]) => {
        setOverview(ov);
        setTrend(tr);
        setError(null);
      })
      .catch(() => setError('加载统计数据失败'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载中...</p>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-red-500">{error || '数据加载失败'}</p>
      </div>
    );
  }

  const feedbackTotal = overview.feedback_positive_count + overview.feedback_negative_count;
  const positiveRatio = feedbackTotal > 0 ? Math.round((overview.feedback_positive_count / feedbackTotal) * 100) : 0;

  const statCards = [
    { label: '用户数', value: overview.total_users, icon: Users },
    { label: '会话数', value: overview.total_sessions, icon: MessagesSquare },
    { label: '消息数', value: overview.total_messages, icon: MessageSquare },
    { label: '文档数', value: overview.total_documents, icon: FileText },
  ];

  const maxCount = Math.max(...trend.map((d) => d.count), 1);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex items-center gap-4 mb-8">
          <button onClick={() => navigate('/chat')} className="p-2 hover:bg-gray-200 rounded-lg transition">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-xl font-bold">管理后台</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">{error}</div>
        )}

        {/* Stat Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {statCards.map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.label} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                    <Icon size={20} className="text-indigo-500" />
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">{card.label}</p>
                    <p className="text-2xl font-bold text-gray-900">{card.value.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Feedback Ratio */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">反馈评价比例</h2>
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <ThumbsUp size={18} className="text-green-500" />
              <span className="text-sm text-gray-600">好评 {overview.feedback_positive_count}</span>
            </div>
            <div className="flex items-center gap-2">
              <ThumbsDown size={18} className="text-red-500" />
              <span className="text-sm text-gray-600">差评 {overview.feedback_negative_count}</span>
            </div>
            <div className="flex-1" />
            <div className="text-right">
              <p className="text-xs text-gray-500">好评率</p>
              <p className="text-lg font-bold" style={{ color: '#6366f1' }}>{positiveRatio}%</p>
            </div>
          </div>
          {feedbackTotal > 0 && (
            <div className="mt-3 w-full bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${positiveRatio}%`,
                  backgroundColor: '#6366f1',
                }}
              />
            </div>
          )}
        </div>

        {/* Daily Trend Bar Chart */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">近7日提问量</h2>
          {trend.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">暂无数据</p>
          ) : (
            <div className="flex items-end justify-between gap-2" style={{ height: '200px' }}>
              {trend.map((item) => {
                const heightPercent = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
                const dateLabel = item.date.slice(5); // MM-DD
                return (
                  <div key={item.date} className="flex flex-col items-center flex-1 h-full justify-end">
                    <span className="text-xs text-gray-500 mb-1">{item.count}</span>
                    <div
                      className="w-full rounded-t-md transition-all"
                      style={{
                        height: `${Math.max(heightPercent, 2)}%`,
                        backgroundColor: '#6366f1',
                      }}
                    />
                    <span className="text-xs text-gray-400 mt-2">{dateLabel}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
