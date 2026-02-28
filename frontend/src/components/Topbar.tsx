import { Download, Bot, RefreshCw, Cpu } from 'lucide-react';

const PAGE_TITLES: Record<string, string> = {
    dashboard: '实时监控大盘',
    groups: '群组监控',
    search: '全库溯源搜索',
    summaries: '全景洞察摘要',
    links: '情报链接网路',
    settings: '偏好设置与状态',
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
        <header className="px-6 md:px-8 py-5 flex flex-col md:flex-row md:justify-between md:items-center border-b border-white/10 backdrop-blur-2xl bg-black/50 sticky top-0 z-[100] gap-4">
            <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10 flex items-center justify-center shadow-lg">
                    <Cpu className="w-5 h-5 text-accent" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                        {title}
                    </h2>
                    <p className="text-[11px] text-text3 font-mono flex items-center gap-1.5 mt-1">
                        <RefreshCw className="w-3 h-3 opacity-60" />
                        上次刷新: {refreshStr} <span className="mx-1">·</span> 60s Auto Sync
                    </p>
                </div>
            </div>

            <div className="flex gap-3">
                <button
                    id="btn-export-csv"
                    onClick={onExportCsv}
                    className="group bg-white/[0.03] border border-white/10 text-text2 px-4 py-2 rounded-xl cursor-pointer text-[13px] font-medium transition-all hover:bg-white/10 hover:text-white hover:border-white/20 active:scale-95 flex items-center gap-2"
                >
                    <Download className="w-4 h-4 text-text3 group-hover:text-accent4 transition-colors" />
                    导出 CSV
                </button>
                <button
                    id="btn-ai-summary"
                    onClick={onSummary}
                    disabled={isSummarizing}
                    className={`relative overflow-hidden group border px-5 py-2 rounded-xl cursor-pointer text-[13px] font-bold transition-all active:scale-95 flex items-center gap-2 ${isSummarizing
                        ? 'border-accent5/30 text-accent5/50 cursor-not-allowed bg-accent5/5'
                        : 'border-accent5/50 text-accent5 bg-accent5/10 hover:bg-accent5/20 hover:border-accent5 hover:shadow-[0_0_15px_rgba(139,92,246,0.3)]'}`}
                >
                    {isSummarizing ? (
                        <>
                            <div className="absolute inset-0 shimmer-bg opacity-20 pointer-events-none" />
                            <RefreshCw className="w-4 h-4 animate-spin" />
                            分析推演中...
                        </>
                    ) : (
                        <>
                            <Bot className="w-4 h-4 group-hover:scale-110 transition-transform" />
                            生成 AI 洞察
                        </>
                    )}
                </button>
            </div>
        </header>
    );
}
