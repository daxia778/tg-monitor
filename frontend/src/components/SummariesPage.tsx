import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Download, ChevronDown, BookOpen, AlertCircle, TrendingUp, Lightbulb } from 'lucide-react';

type Summary = {
    id: number;
    content: string;
    hours: number;
    created_at: string;
    group_id?: number;
};

// Helper to extract tags from content
function extractTags(content: string) {
    const tags: { type: string, label: string }[] = [];
    if (content.includes('【风险提示】') || content.includes('风险')) tags.push({ type: 'danger', label: '风险提示' });
    if (content.includes('【行动建议】') || content.includes('建议')) tags.push({ type: 'warning', label: '行动建议' });
    if (content.includes('【热点讨论】') || content.includes('热点')) tags.push({ type: 'success', label: '热点追踪' });
    if (tags.length === 0) tags.push({ type: 'info', label: '常规简报' });
    return tags;
}

const tagStyles: Record<string, { bg: string, text: string, icon: any }> = {
    danger: { bg: 'bg-red-500/10', text: 'text-red-400', icon: AlertCircle },
    warning: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', icon: Lightbulb },
    success: { bg: 'bg-green-500/10', text: 'text-green-400', icon: TrendingUp },
    info: { bg: 'bg-blue-500/10', text: 'text-blue-400', icon: BookOpen },
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
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6].map(i => (
                    <div key={i} className="h-48 rounded-2xl bg-white/[0.03] animate-pulse border border-border-subtle" />
                ))}
            </div>
        );
    }

    if (summaries.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-20 glass-panel rounded-2xl border border-white/5">
                <BookOpen className="w-16 h-16 text-text3 mb-4 opacity-50" />
                <div className="text-text2 font-medium">知识库尚为空白</div>
                <div className="text-text3 text-sm mt-2">在顶栏点击「AI 智能摘要」生成首份洞察报告</div>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-max">
            {summaries.map((s, i) => {
                const tags = extractTags(s.content);
                const isExpanded = expanded === s.id;
                return (
                    <motion.div
                        key={s.id ?? i}
                        initial={{ opacity: 0, scale: 0.95, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className={`glass-panel rounded-2xl border border-white/5 overflow-hidden transition-all duration-300 ${isExpanded ? 'col-span-1 md:col-span-2 lg:col-span-3' : 'hover:-translate-y-1 hover:border-white/20'}`}
                    >
                        <div className="p-5 flex flex-col h-full cursor-pointer" onClick={() => setExpanded(isExpanded ? null : s.id)}>
                            <div className="flex justify-between items-start mb-4">
                                <div>
                                    <div className="text-[10px] text-text3 font-mono tracking-wider uppercase mb-1">{formatDate(s.created_at)}</div>
                                    <h3 className="text-base font-bold text-white leading-tight">
                                        基于 {s.hours ?? 24}H 周期的态势追踪报告
                                    </h3>
                                </div>
                                <button
                                    className="p-1.5 rounded-md hover:bg-white/10 text-text3 hover:text-white transition-colors border-0 bg-transparent flex-shrink-0 z-10"
                                    onClick={(e) => { e.stopPropagation(); alert('导出长图功能开发中...'); }}
                                    title="导出为社交分享图"
                                >
                                    <Download className="w-4 h-4" />
                                </button>
                            </div>

                            <div className="flex flex-wrap gap-2 mb-4">
                                {tags.map((tag, j) => {
                                    const TagIcon = tagStyles[tag.type].icon;
                                    return (
                                        <div key={j} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-white/5 ${tagStyles[tag.type].bg} ${tagStyles[tag.type].text}`}>
                                            <TagIcon className="w-3 h-3" />
                                            <span className="text-[10px] font-medium">{tag.label}</span>
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="relative flex-1">
                                <div className={`text-[13px] text-text2 leading-relaxed whitespace-pre-wrap break-words font-sans transition-all duration-300 ${isExpanded ? 'line-clamp-none' : 'line-clamp-4'}`}>
                                    {s.content}
                                </div>
                                {!isExpanded && (
                                    <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-[var(--color-bg-card)] to-transparent pointer-events-none" />
                                )}
                            </div>

                            <div className="mt-4 pt-3 border-t border-white/5 flex justify-center text-text3">
                                <motion.div animate={{ rotate: isExpanded ? 180 : 0 }} transition={{ duration: 0.3 }}>
                                    <ChevronDown className="w-4 h-4" />
                                </motion.div>
                            </div>
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}

function formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
        return dateStr;
    }
}
