
const PAGE_TITLES: Record<string, string> = {
    dashboard: '实时监控大盘',
    groups: '群组监控',
    search: '全库搜索',
    summaries: '所有摘要',
    links: '链接收集',
};

interface TopbarProps {
    page: string;
    onExportCsv: () => void;
    onSummary: () => void;
    isSummarizing: boolean;
    lastRefresh: Date | null;
}

export function Topbar({ page, onExportCsv, onSummary, isSummarizing, lastRefresh }: TopbarProps) {
    const title = PAGE_TITLES[page] ?? '实时监控大盘';
    const refreshStr = lastRefresh
        ? lastRefresh.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        : '—';

    return (
        <header className="px-8 py-4 flex justify-between items-center border-b border-border-subtle backdrop-blur-xl bg-bg-primary/70 sticky top-0 z-10">
            <div>
                <h2 className="text-lg font-semibold text-text-main">{title}</h2>
                <p className="text-[11px] text-text3 mt-0.5">上次刷新: {refreshStr} · 每60s自动更新</p>
            </div>

            <div className="flex gap-2.5">
                <button
                    id="btn-export-csv"
                    onClick={onExportCsv}
                    className="bg-transparent border border-border-subtle text-text2 px-4 py-2 rounded-lg cursor-pointer text-[13px] font-medium transition-all hover:bg-bg-hover hover:text-text-main hover:border-white/20 active:scale-95 flex items-center gap-1.5"
                >
                    <span>📥</span> 导出 CSV
                </button>
                <button
                    id="btn-ai-summary"
                    onClick={onSummary}
                    disabled={isSummarizing}
                    className={`border border-accent text-accent px-4 py-2 rounded-lg cursor-pointer text-[13px] font-medium transition-all active:scale-95 flex items-center gap-1.5 ${isSummarizing ? 'opacity-60 cursor-not-allowed' : 'bg-bg-hover hover:opacity-90'
                        }`}
                >
                    <span>{isSummarizing ? '⏳' : '🤖'}</span>
                    {isSummarizing ? 'AI 生成中...' : 'AI 智能摘要'}
                </button>
            </div>
        </header>
    );
}
