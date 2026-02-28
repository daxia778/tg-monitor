import { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Topbar } from './components/Topbar';
import { StatCards } from './components/StatCards';
import { MessageList } from './components/MessageList';
import type { Message } from './components/MessageList';
import { GroupList } from './components/GroupList';
import type { GroupStat } from './components/GroupList';
import { SearchPage } from './components/SearchPage';
import { SummariesPage } from './components/SummariesPage';
import { LinksPage } from './components/LinksPage';
import { SettingsPage } from './components/SettingsPage';

type OverviewData = {
  total_messages: number;
  last_24h: number;
  group_count: number;
  model: string;
};

// ─── AI Summary Modal ──────────────────────────────────────────────
function SummaryModal({ taskId, onClose }: { taskId: string; onClose: () => void }) {
  const [status, setStatus] = useState<string>('running');
  const [progress, setProgress] = useState<string>('正在初始化...');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(10);

  useEffect(() => {
    const poll = setInterval(async () => {
      try {
        const res = await fetch(`/api/summary/status/${taskId}`);
        const data = await res.json();
        setStatus(data.status);
        setProgress(data.progress ?? '');
        setCurrent(data.current_step ?? 0);
        setTotal(data.total_steps ?? 10);
        if (data.status === 'done') {
          setResult(data.result);
          clearInterval(poll);
        } else if (data.status === 'error') {
          setError(data.error);
          clearInterval(poll);
        }
      } catch {
        clearInterval(poll);
        setError('轮询失败，请检查网络');
      }
    }, 1500);
    return () => clearInterval(poll);
  }, [taskId]);

  const pct = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <div className="fixed inset-0 z-[500] flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="glass-panel w-full max-w-2xl rounded-2xl p-6 shadow-2xl relative overflow-hidden transition-all duration-300">

        {/* Shimmer background animation when running */}
        {status === 'running' && (
          <div className="absolute inset-0 shimmer-bg opacity-30 pointer-events-none" />
        )}

        <div className="flex justify-between items-center mb-6 relative z-10">
          <h3 className="text-lg font-bold flex items-center gap-2 text-white tracking-wide">
            <span className={status === 'running' ? 'animate-pulse glow-ai text-accent5' : 'text-accent5'}>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            </span>
            AI 智能态势感知
          </h3>
          <button
            onClick={onClose}
            className="text-text3 hover:text-white transition-colors duration-200 bg-white/5 hover:bg-white/10 p-1.5 rounded-md"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>

        <div className="relative z-10">
          {status === 'running' && (
            <div className="py-8">
              <div className="flex justify-between items-end mb-3">
                <div className="text-sm text-text2 font-mono tracking-tight animate-pulse flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-accent5 glow-ai" />
                  {progress}
                </div>
                <div className="text-[12px] text-accent5 font-mono">{current}/{total}</div>
              </div>
              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent5 transition-all duration-[800ms] shadow-[0_0_15px_rgba(139,92,246,0.5)]"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )}

          {status === 'done' && result && (
            <div className="animate-in fade-in zoom-in-95 duration-500">
              <div className="text-[12px] text-accent4 mb-3 font-mono flex items-center gap-2 tracking-widest uppercase">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                分析已就绪
              </div>
              <pre className="text-[13px] text-white/90 leading-relaxed whitespace-pre-wrap break-words font-sans bg-black/40 rounded-xl p-5 max-h-[60vh] overflow-y-auto border border-white/5 shadow-inner">
                {result}
              </pre>
            </div>
          )}

          {status === 'error' && (
            <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl p-5 flex items-start gap-3">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
              <div>
                <div className="font-semibold mb-1">系统分析遭遇异常</div>
                <div className="opacity-80">{error}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState('dashboard');
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [recentMsgs, setRecentMsgs] = useState<Message[]>([]);
  const [groups, setGroups] = useState<GroupStat[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryTaskId, setSummaryTaskId] = useState<string | null>(null);

  const hitKeywords = recentMsgs.reduce(
    (acc, msg) => acc + (msg.alert_keywords?.length || 0),
    0,
  );

  // ─── Data fetch ─────────────────────
  const fetchData = useCallback(async () => {
    try {
      const [overviewRes, groupsRes, msgsRes] = await Promise.all([
        fetch('/api/overview'),
        fetch('/api/groups?hours=24'),
        fetch('/api/recent_messages?limit=100'),
      ]);
      if (overviewRes.ok) setOverview(await overviewRes.json());
      if (groupsRes.ok) {
        const d = await groupsRes.json();
        // API returns data array with message_count / active_users
        setGroups((d.data || []).slice(0, 10));
      }
      if (msgsRes.ok) {
        const d = await msgsRes.json();
        // Reverse array so newest messages appear at the top
        setRecentMsgs((d.data || []).reverse());
      }
      setLastRefresh(new Date());
    } catch (e) {
      console.error('Fetch error:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    // 60 second auto refresh
    const timer = setInterval(fetchData, 60_000);
    return () => clearInterval(timer);
  }, [fetchData]);

  // ─── CSV export ─────────────────────
  const handleExportCsv = () => {
    const url = `/api/export?hours=24`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `tg_monitor_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  // ─── AI Summary ─────────────────────
  const handleSummary = async () => {
    if (isSummarizing) return;
    setIsSummarizing(true);
    try {
      const res = await fetch('/api/summary/generate?hours=24&mode=quick', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSummaryTaskId(data.task_id);
      } else {
        alert('启动摘要任务失败，请检查 AI 代理是否在线');
        setIsSummarizing(false);
      }
    } catch {
      alert('网络错误，无法连接后端');
      setIsSummarizing(false);
    }
  };

  const closeSummaryModal = () => {
    setSummaryTaskId(null);
    setIsSummarizing(false);
  };

  // ─── Render page content ─────────────
  const renderContent = () => {
    switch (page) {
      case 'dashboard':
        return (
          <>
            <StatCards
              totalMessages={overview?.total_messages ?? '...'}
              last24hMessages={overview?.last_24h ?? '...'}
              alertKeyword={hitKeywords}
              groupCount={overview?.group_count ?? '...'}
              aiModel={overview?.model ?? '...'}
            />
            <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-5">
              <MessageList messages={recentMsgs} isLoading={isLoading} />
              <GroupList groups={groups} isLoading={isLoading} />
            </div>
          </>
        );
      case 'groups':
        return (
          <div className="max-w-3xl">
            <GroupList groups={groups} isLoading={isLoading} />
          </div>
        );
      case 'search':
        return <SearchPage />;
      case 'summaries':
        return <SummariesPage />;
      case 'links':
        return <LinksPage />;
      case 'settings':
        return <SettingsPage />;
      default:
        return null;
    }
  };

  return (
    <div className="flex w-full min-h-screen">
      <Sidebar activeItem={page} onNavigate={setPage} />

      <main className="flex-1 ml-[220px] min-h-screen flex flex-col">
        <Topbar
          page={page}
          onExportCsv={handleExportCsv}
          onSummary={handleSummary}
          isSummarizing={isSummarizing}
          lastRefresh={lastRefresh}
        />

        <div className="p-6 md:p-8 flex-1">
          {renderContent()}
        </div>
      </main>

      {summaryTaskId && (
        <SummaryModal taskId={summaryTaskId} onClose={closeSummaryModal} />
      )}
    </div>
  );
}
