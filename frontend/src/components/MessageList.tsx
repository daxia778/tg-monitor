
export type Message = {
    id: number;
    group_id: number;
    group_title?: string;
    sender_name: string;
    text: string;
    date: string;
    alert_keywords?: string[];
};

export function MessageList({ messages, isLoading }: { messages: Message[]; isLoading: boolean }) {
    return (
        <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
            <div className="py-4 px-5 border-b border-border-subtle flex justify-between items-center bg-white/[0.03]">
                <h3 className="text-sm font-semibold flex items-center gap-1.5">
                    <span>💬</span> 监听消息流
                </h3>
                <span className="text-[11px] text-text3 bg-bg-primary px-2 py-0.5 rounded-full border border-border-subtle">实时更新</span>
            </div>

            <div className="max-h-[520px] overflow-y-auto">
                {isLoading ? (
                    <div className="p-5 space-y-3">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-14 rounded-xl bg-gradient-to-r from-white/[0.03] via-white/[0.07] to-white/[0.03] animate-pulse border border-border-subtle" />
                        ))}
                    </div>
                ) : messages.length === 0 ? (
                    <div className="text-center text-text3 py-12 text-[13px]">暂无消息数据</div>
                ) : (
                    <div className="divide-y divide-border-subtle">
                        {messages.map((msg, i) => (
                            <div key={i} className="px-5 py-3 hover:bg-white/[0.02] transition-colors">
                                <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                                    <span className="text-[10px] text-text3 font-mono tabular-nums">
                                        {formatDate(msg.date)}
                                    </span>
                                    {msg.group_title && (
                                        <span className="text-[10px] text-accent2 px-1.5 py-px bg-accent2/10 rounded-full">
                                            {msg.group_title}
                                        </span>
                                    )}
                                    <span className="text-[11px] text-accent font-medium">
                                        {msg.sender_name || 'Unknown'}
                                    </span>
                                    {msg.alert_keywords?.map(kw => (
                                        <span key={kw} className="text-[10px] px-1.5 py-px bg-red-500/10 text-red-400 rounded-full border border-red-500/20">
                                            ⚠ {kw}
                                        </span>
                                    ))}
                                </div>
                                <div className="text-xs text-text2 leading-relaxed break-words line-clamp-3">
                                    {msg.text ? msg.text : <span className="text-text3 italic">[媒体文件]</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}

function formatDate(dateStr: string): string {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        return d.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch {
        return dateStr;
    }
}
