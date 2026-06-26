import { useState, useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import { decomposeRequirement } from '../api/agent';
import type { DecomposeTask, DecomposeResponse } from '../api/agent';

interface MermaidAPI {
  initialize(config: Record<string, unknown>): void;
  run(opts: { nodes: HTMLElement[] }): Promise<void>;
}

function buildMermaid(tasks: DecomposeTask[]): string {
  const idMap: Record<number, string> = {};
  tasks.forEach((t) => {
    idMap[t.id] = `task_${t.id}`;
  });

  const lines: string[] = ['flowchart TD'];
  tasks.forEach((t) => {
    const label = t.description.replace(/"/g, '#quot;');
    lines.push(`  ${idMap[t.id]}["${label}<br/><i>${t.service}</i>"]`);
  });
  tasks.forEach((t) => {
    t.dependencies.forEach((dep) => {
      if (idMap[dep] !== undefined) {
        lines.push(`  ${idMap[dep]} --> ${idMap[t.id]}`);
      }
    });
  });
  return lines.join('\n');
}

export function AgentPage() {
  const [requirement, setRequirement] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DecomposeResponse | null>(null);
  const mermaidRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!result || !mermaidRef.current) return;

    const el = mermaidRef.current;
    el.innerHTML = '';

    const containerId = 'mermaid-container-' + Date.now();
    const container = document.createElement('div');
    container.id = containerId;
    container.textContent = buildMermaid(result.tasks);
    container.className = 'mermaid';
    el.appendChild(container);

    const existingScript = document.querySelector('script[data-mermaid]');
    if (existingScript) {
      existingScript.remove();
    }

    const script = document.createElement('script');
    script.setAttribute('data-mermaid', 'true');
    script.src = 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';
    script.onload = () => {
      const mermaid = (window as unknown as Record<string, unknown>).mermaid as MermaidAPI | undefined;
      if (mermaid) {
        mermaid.initialize({ startOnLoad: true, theme: 'default' });
        mermaid.run({ nodes: [container] });
      }
    };
    document.body.appendChild(script);

    return () => {
      const s = document.querySelector('script[data-mermaid]');
      if (s) s.remove();
    };
  }, [result]);

  const handleAnalyze = async () => {
    if (!requirement.trim()) return;
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await decomposeRequirement(requirement.trim());
      setResult(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '分析失败，请重试';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const phaseGroups = result
    ? result.parallel_groups.map((groupTaskIds, i) => {
        const tasks = groupTaskIds
          .map((id) => result.tasks.find((t) => t.id === id))
          .filter((t): t is DecomposeTask => t !== undefined);
        return [i, tasks] as const;
      })
    : [];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">AI Agent 任务拆解</h1>
          <p className="mt-2 text-sm text-gray-500">
            输入业务需求，AI 将自动拆解为可执行的任务单元，分析受影响的微服务、任务依赖关系和并行执行策略
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-8">
          <label htmlFor="requirement" className="block text-sm font-medium text-gray-700 mb-2">
            需求描述
          </label>
          <textarea
            id="requirement"
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            placeholder="例如：用户下单后自动发送短信通知"
            rows={4}
            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition resize-none"
            disabled={loading}
          />
          <button
            onClick={handleAnalyze}
            disabled={loading || !requirement.trim()}
            className="mt-4 flex items-center gap-2 px-6 py-2.5 bg-indigo-500 text-white rounded-lg font-medium hover:bg-indigo-600 disabled:opacity-50 transition"
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" /> 分析中...
              </>
            ) : (
              '开始分析'
            )}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-8">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={32} className="animate-spin text-indigo-500" />
            <span className="ml-3 text-gray-500">正在分析需求...</span>
          </div>
        )}

        {result && (
          <div className="space-y-8">
            <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">受影响的服务</h2>
              <div className="flex flex-wrap gap-2">
                {result.services.map((svc) => {
                  const colors: Record<string, string> = {
                    用户服务: 'bg-blue-100 text-blue-700',
                    订单服务: 'bg-green-100 text-green-700',
                    通知服务: 'bg-yellow-100 text-yellow-700',
                    支付服务: 'bg-purple-100 text-purple-700',
                    商品服务: 'bg-pink-100 text-pink-700',
                    库存服务: 'bg-orange-100 text-orange-700',
                    短信服务: 'bg-cyan-100 text-cyan-700',
                  };
                  const colorClass = colors[svc] || 'bg-indigo-100 text-indigo-700';
                  return (
                    <span key={svc} className={`px-3 py-1 rounded-full text-xs font-medium ${colorClass}`}>
                      {svc}
                    </span>
                  );
                })}
              </div>
            </section>

            <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">任务依赖表</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-3 text-gray-500 font-medium">ID</th>
                      <th className="text-left py-3 px-3 text-gray-500 font-medium">任务</th>
                      <th className="text-left py-3 px-3 text-gray-500 font-medium">服务</th>
                      <th className="text-left py-3 px-3 text-gray-500 font-medium">依赖</th>
                      <th className="text-left py-3 px-3 text-gray-500 font-medium">可并行</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.tasks.map((task) => (
                      <tr key={task.id} className="border-b border-gray-100">
                        <td className="py-3 px-3 font-mono text-xs text-gray-500">{task.id}</td>
                        <td className="py-3 px-3 text-gray-800">{task.description}</td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">{task.service}</span>
                        </td>
                        <td className="py-3 px-3 text-gray-500 text-xs">
                          {task.dependencies.length > 0 ? task.dependencies.join(', ') : '—'}
                        </td>
                        <td className="py-3 px-3">
                          {task.dependencies.length === 0 ? (
                            <span className="text-green-600 text-xs">是</span>
                          ) : (
                            <span className="text-gray-400 text-xs">否</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">执行阶段</h2>
              <div className="space-y-4">
                {phaseGroups.map(([group, tasks], i) => (
                  <div key={group} className="border border-gray-200 rounded-xl p-4">
                    <h3 className="text-sm font-semibold text-indigo-600 mb-3">阶段 {i + 1}</h3>
                    <div className="flex flex-wrap gap-2">
                      {tasks.map((t) => (
                        <span key={t.id} className="px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700">
                          {t.description}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">任务依赖流程图</h2>
              <div ref={mermaidRef} className="flex justify-center overflow-x-auto" />
            </section>

            <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">分析说明</h2>
              <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-wrap">
                {result.explanation}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
