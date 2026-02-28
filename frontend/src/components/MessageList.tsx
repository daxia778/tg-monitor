import { motion, AnimatePresence } from 'framer-motion';

export type Message = {
    id: number;
    group_id: number;
    group_title?: string;
    sender_name: string;
    text: string;
    date: string;
    alert_keywords?: string[];
};

// Helper: Generate consistent HSL colors based on the sender's name string (like Telegram)
function stringToColor(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const h = Math.abs(hash) % 360;
    return `hsl(${h}, 70%, 65%)`; // pastels/vibes
}

// Helper: Get initials for avatar
function getInitials(name: string): string {
    return name.substring(0, 2).toUpperCase();
}

export function MessageList({ messages, isLoading }: { messages: Message[]; isLoading: boolean }) {
    return (
        <div className="glass-panel rounded-[20px] overflow-hidden flex flex-col h-[600px] relative z-10">
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/10 flex justify-between items-center bg-black/40 backdrop-blur-md relative z-20">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full bg-accent4 animate-pulse shadow-[0_0_10px_#0ea5e9]" />
                    <h3 className="text-[15px] font-semibold tracking-wide text-white">
                        实时态势脉流
                    </h3>
                </div>
                <div className="flex gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-accent4 bg-accent4/10 px-2.5 py-1 rounded-md border border-accent4/20 shadow-[inset_0_1px_1px_rgba(255,255,255,0.1)]">Live</span>
                </div>
            </div>

            {/* List Body */}
            <div className="flex-1 overflow-y-auto w-full custom-scrollbar relative z-10 bg-black/20">
                {isLoading ? (
                    <div className="p-6 space-y-5">
                        {[1, 2, 3, 4].map(i => (
                            <div key={i} className="flex gap-4 w-full opacity-50">
                                <div className="w-10 h-10 rounded-full bg-white/5 animate-pulse shrink-0 border border-white/10" />
                                <div className="flex-1 space-y-2 py-1">
                                    <div className="h-3 w-32 bg-white/5 rounded-md animate-pulse" />
                                    <div className="h-4 w-3/4 bg-white/5 rounded-md animate-pulse" />
                                </div>
                            </div>
                        ))}
                    </div>
                ) : messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-text3 text-sm">暂无拦截数据</div>
                ) : (
                    <div className="px-5 py-4 space-y-6">
                        <AnimatePresence initial={false}>
                            {messages.map((msg, i) => {
                                const avatarColor = stringToColor(msg.sender_name || 'Anonymous');
                                const initials = getInitials(msg.sender_name || '??');

                                return (
                                    <motion.div
                                        key={msg.id ?? i}
                                        layout
                                        initial={{ opacity: 0, y: -20, scale: 0.95 }}
                                        animate={{ opacity: 1, y: 0, scale: 1 }}
                                        transition={{ type: "spring", stiffness: 350, damping: 25 }}
                                        className="flex gap-3.5 group relative"
                                    >
                                        <div className="absolute -left-2 top-0 bottom-0 w-[2px] bg-gradient-to-b from-white/20 to-transparent rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />

                                        {/* Avatar */}
                                        <div
                                            className="w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold shrink-0 shadow-[0_4px_10px_rgba(0,0,0,0.5)] text-bg-primary transition-transform duration-300 group-hover:scale-110 group-hover:shadow-[0_0_15px_currentColor]"
                                            style={{ backgroundColor: avatarColor, color: avatarColor }}
                                        >
                                            <span className="text-black">{initials}</span>
                                        </div>

                                        {/* Message Content Bubble */}
                                        <div className="flex-1 min-w-0 pt-0.5">
                                            <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                                                <span
                                                    className="text-[13px] font-bold tracking-tight truncate max-w-[150px]"
                                                    style={{ color: avatarColor }}
                                                >
                                                    {msg.sender_name || 'Unknown'}
                                                </span>

                                                {msg.group_title && (
                                                    <span className="text-[10px] text-text2 px-1.5 py-0.5 rounded-md bg-white/5 border border-white/10 truncate max-w-[120px]">
                                                        {msg.group_title}
                                                    </span>
                                                )}

                                                <span className="text-[10px] text-text3 font-mono tabular-nums ml-auto relative top-px">
                                                    {formatDate(msg.date)}
                                                </span>
                                            </div>

                                            <div className="bg-white/5 border border-white/10 rounded-tl-none rounded-2xl px-4 py-3 text-[13px] text-text-main leading-relaxed shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] transition-colors group-hover:bg-white/10 backdrop-blur-sm relative overflow-hidden">
                                                {msg.text ? (
                                                    <span className="break-words line-clamp-4 relative z-10">{msg.text}</span>
                                                ) : (
                                                    <span className="text-text3 italic flex items-center gap-1 relative z-10">
                                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                                                        [媒体附件]
                                                    </span>
                                                )}

                                                {/* Alert Tags directly inside the bubble bottom */}
                                                {msg.alert_keywords && msg.alert_keywords.length > 0 && (
                                                    <div className="mt-2.5 flex gap-1.5 flex-wrap relative z-10">
                                                        {msg.alert_keywords.map(kw => (
                                                            <span key={kw} className="flex items-center gap-1 text-[10px] px-2 py-0.5 bg-red-500/20 text-red-300 rounded border border-red-500/40 font-medium shadow-[0_0_8px_rgba(239,68,68,0.2)]">
                                                                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                                                                {kw}
                                                            </span>
                                                        ))}
                                                    </div>
                                                )}

                                                <div className="absolute -top-10 -right-10 w-20 h-20 bg-white/5 rounded-full blur-xl group-hover:bg-white/10 transition-colors pointer-events-none" />
                                            </div>
                                        </div>
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                    </div>
                )}
            </div>

            <style>{`
                .custom-scrollbar::-webkit-scrollbar {
                    width: 4px;
                }
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: transparent;
                }
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                }
                .custom-scrollbar:hover::-webkit-scrollbar-thumb {
                    background: rgba(255, 255, 255, 0.2);
                }
            `}</style>
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
