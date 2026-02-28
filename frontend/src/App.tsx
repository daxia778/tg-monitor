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
    <div className="fixed inset-0 z-[500] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-bg-secondary border border-border-subtle rounded-2xl w-full max-w-2xl mx-4 p-6 shadow-2xl">
        <div className="flex justify-between items-center mb-5">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <span>🤖</span> AI 智能摘要
          </h3>
          <button
            id="modal-close"
            onClick={onClose}
            className="text-text3 hover:text-text-main text-xl bg-transparent border-0 cursor-pointer"
          >✕</button>
        </div>

        {status === 'running' && (
          <>
            <div className="text-sm text-text2 mb-3">{progress}</div>
            <div className="h-2 bg-border-subtle rounded-full overflow-hidden mb-1">
              <div
                className="h-full bg-accent transition-all duration-500 rounded-full"
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="text-[11px] text-text3 text-right">{current}/{total}</div>
          </>
        )}

        {status === 'done' && result && (
          <>
            <div className="text-[11px] text-accent4 mb-3">✅ 生成完成</div>
            <pre className="text-[12px] text-text2 leading-relaxed whitespace-pre-wrap break-words font-sans bg-bg-primary/60 rounded-xl p-4 max-h-[60vh] overflow-y-auto border border-border-subtle">
              {result}
            </pre>
          </>
        )}

        {status === 'error' && (
          <div className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            ❌ {error}
          </div>
        )}
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
        setRecentMsgs(d.data || []);
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
