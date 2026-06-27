import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStatsOverview, getDailyTrend, getFeedbackSessions, type StatsOverview, type DailyTrendItem, type FeedbackSession } from '../api/stats';
import { ArrowLeft, Users, MessageSquare, FileText, MessagesSquare, ThumbsUp, ThumbsDown } from 'lucide-react';

export function StatsPage() {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [trend, setTrend] = useState<DailyTrendItem[]>([]);
  const [feedbackSessions, setFeedbackSessions] = useState<FeedbackSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getStatsOverview(), getDailyTrend(7), getFeedbackSessions()])
      .then(([ov, tr, fs]) => {
        setOverview(ov);
        setTrend(tr);
        setFeedbackSessions(fs);
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

        {/* Daily Trend Line Chart */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">近7日提问量</h2>
          {trend.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">暂无数据</p>
          ) : (
            (() => {
              const W = 560, H = 220, PAD_L = 36, PAD_R = 16, PAD_T = 30, PAD_B = 28;
              const plotW = W - PAD_L - PAD_R;
              const plotH = H - PAD_T - PAD_B;

              const points = trend.map((d, i) => ({
                x: PAD_L + (trend.length === 1 ? plotW / 2 : (i / (trend.length - 1)) * plotW),
                y: PAD_T + plotH - (maxCount > 0 ? (d.count / maxCount) * plotH : 0),
                count: d.count,
                label: d.date.slice(5),
              }));

              const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
              const areaPath = linePath + ` L${points[points.length - 1].x},${PAD_T + plotH} L${points[0].x},${PAD_T + plotH} Z`;

              return (
                <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: '240px' }}>
                  <defs>
                    <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  {/* Y axis grid lines */}
                  {[0, 0.25, 0.5, 0.75, 1].map((r) => (
                    <line key={r}
                      x1={PAD_L} y1={PAD_T + plotH * (1 - r)}
                      x2={PAD_L + plotW} y2={PAD_T + plotH * (1 - r)}
                      stroke="#f0f0f0" strokeWidth="1"
                    />
                  ))}
                  {/* Area fill */}
                  <path d={areaPath} fill="url(#lineGrad)" />
                  {/* Line */}
                  <path d={linePath} fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  {/* Data points */}
                  {points.map((p, i) => (
                    <g key={i}>
                      <circle cx={p.x} cy={p.y} r="4" fill="#fff" stroke="#6366f1" strokeWidth="2" />
                      <text x={p.x} y={p.y - 10} textAnchor="middle" fill="#6366f1" fontSize="11" fontWeight="600">
                        {p.count}
                      </text>
                      <text x={p.x} y={H - 6} textAnchor="middle" fill="#9ca3af" fontSize="11">
                        {p.label}
                      </text>
                    </g>
                  ))}
                  {/* Y axis labels */}
                  <text x={PAD_L - 6} y={PAD_T + 4} textAnchor="end" fill="#9ca3af" fontSize="10">{maxCount}</text>
                  <text x={PAD_L - 6} y={PAD_T + plotH + 2} textAnchor="end" fill="#9ca3af" fontSize="10">0</text>
                </svg>
              );
            })()
          )}
        </div>

        {/* Feedback Sessions Table */}
        {feedbackSessions.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">会话评价明细</h2>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs text-gray-500">
                  <th className="text-left py-2 font-medium">会话标题</th>
                  <th className="text-center py-2 font-medium w-20">
                    <ThumbsUp size={12} className="inline text-green-500" /> 赞
                  </th>
                  <th className="text-center py-2 font-medium w-20">
                    <ThumbsDown size={12} className="inline text-red-500" /> 踩
                  </th>
                </tr>
              </thead>
              <tbody>
                {feedbackSessions.map((fs) => (
                  <tr key={fs.session_id} className="border-b border-gray-50">
                    <td className="py-2 text-gray-700 truncate max-w-[200px]">{fs.title || `会话 #${fs.session_id}`}</td>
                    <td className="text-center py-2 text-green-600">{fs.positive_count}</td>
                    <td className="text-center py-2 text-red-500">{fs.negative_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
