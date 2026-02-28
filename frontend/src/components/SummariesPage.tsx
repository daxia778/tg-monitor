import { useState, useEffect } from 'react';

type Summary = {
    id: number;
    content: string;
    hours: number;
    created_at: string;
    group_id?: number;
};

export function SummariesPage() {
    const [summaries, setSummaries] = useState<Summary[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [expanded, setExpanded] = useState<number | null>(null);

    useEffect(() => {
        fetch('/api/summary/history?limit=20')
            .then(r => r.json())
            .then(d => setSummaries(d.data || []))
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, []);

    if (isLoading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3].map(i => (
                    <div key={i} className="h-24 rounded-[14px] bg-white/[0.03] animate-pulse border border-border-subtle" />
                ))}
            </div>
        );
    }

    if (summaries.length === 0) {
        return (
            <div className="bg-bg-card rounded-[14px] border border-border-subtle p-10 text-center">
                <div className="text-3xl mb-3">📝</div>
                <div className="text-text2 text-sm">还没有生成过摘要</div>
                <div className="text-text3 text-xs mt-1">在顶栏点击「AI 智能摘要」开始生成</div>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {summaries.map((s, i) => (
                <div key={s.id ?? i} className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
                    <button
                        id={`summary-${s.id}`}
                        onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                        className="w-full py-4 px-5 flex justify-between items-center text-left hover:bg-white/[0.02] transition-colors cursor-pointer border-0 bg-transparent"
                    >
                        <div>
                            <div className="text-sm font-semibold text-text-main">
                                📊 摘要 · 最近 {s.hours ?? 24}h
                            </div>
                            <div className="text-[11px] text-text3 mt-0.5">{formatDate(s.created_at)}</div>
                        </div>
                        <span className="text-text3 text-lg">{expanded === s.id ? '▲' : '▼'}</span>
                    </button>
                    {expanded === s.id && (
                        <div className="px-5 pb-5 border-t border-border-subtle">
                            <pre className="text-[12px] text-text2 leading-relaxed whitespace-pre-wrap break-words font-sans mt-4">
                                {s.content}
                            </pre>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
}

function formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    try {
        return new Date(dateStr).toLocaleString('zh-CN');
    } catch {
        return dateStr;
    }
}
