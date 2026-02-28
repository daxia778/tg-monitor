import { motion, AnimatePresence } from 'framer-motion';
import { Users, MessageSquare, TrendingUp } from 'lucide-react';

// 与后端 /api/groups 响应字段保持一致
export type GroupStat = {
    group_id: number;
    title: string;
    message_count: number;
    active_users: number;
    last_msg?: string;
};

export function GroupList({ groups, isLoading }: { groups: GroupStat[]; isLoading: boolean }) {
    // 防空数组时 Math.max 返回 -Infinity
    const maxCount = groups.length > 0 ? Math.max(...groups.map(g => g.message_count)) : 1;

    return (
        <div className="glass-panel rounded-[20px] overflow-hidden flex flex-col h-[600px] relative z-10">
            <div className="px-6 py-4 border-b border-white/10 flex justify-between items-center bg-black/40 backdrop-blur-md relative z-20">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-accent2/10 flex items-center justify-center border border-accent2/20 shrink-0">
                        <TrendingUp className="w-4 h-4 text-accent2" />
                    </div>
                    <h3 className="text-[15px] font-semibold tracking-wide text-white">群组热度榜</h3>
                </div>
                <span className="text-[10px] text-accent2 bg-accent2/10 px-2.5 py-1 rounded-md border border-accent2/20 tracking-wider">
                    TOP {Math.min(groups.length, 10)}
                </span>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 custom-scrollbar bg-black/20">
                {isLoading ? (
                    <div className="space-y-4">
                        {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} />)}
                    </div>
                ) : groups.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-text3 text-sm">暂无数据</div>
                ) : (
                    <div className="space-y-3">
                        <AnimatePresence initial={false}>
                            {groups.map((g, i) => (
                                <motion.div
                                    key={g.group_id}
                                    initial={{ opacity: 0, x: 20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: i * 0.05, type: 'spring', stiffness: 300, damping: 25 }}
                                    className="group relative bg-white/5 border border-white/10 p-3 rounded-xl hover:bg-white/10 transition-colors cursor-pointer overflow-hidden"
                                >
                                    <div className="flex justify-between items-start mb-2 relative z-10">
                                        <div className="text-[13px] font-bold text-white truncate max-w-[70%] group-hover:text-accent2 transition-colors">
                                            {g.title}
                                        </div>
                                        <div className="flex items-center gap-1 bg-white/10 px-2 py-0.5 rounded-full border border-white/5">
                                            <MessageSquare className="w-3 h-3 text-accent2" />
                                            <span className="text-xs font-mono font-semibold text-white">{g.message_count.toLocaleString()}</span>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-4 text-[11px] text-text3 mb-3 relative z-10">
                                        <div className="flex items-center gap-1.5 bg-black/30 px-2 py-1 rounded-lg border border-white/5">
                                            <Users className="w-3 h-3 opacity-70" />
                                            <span>{g.active_users} 活跃</span>
                                        </div>
                                    </div>

                                    <div className="h-1.5 bg-black/40 rounded-full overflow-hidden border border-white/5 relative z-10">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${Math.min(100, (g.message_count / maxCount) * 100)}%` }}
                                            transition={{ duration: 1, ease: "easeOut", delay: i * 0.1 }}
                                            className="h-full bg-gradient-to-r from-accent2/50 to-accent4 rounded-full relative"
                                        >
                                            <div className="absolute top-0 right-0 bottom-0 w-4 bg-white/40 blur-sm mix-blend-overlay" />
                                        </motion.div>
                                    </div>

                                    {/* Subtitle Glow */}
                                    <div className="absolute -bottom-4 -right-4 w-16 h-16 bg-accent2/20 blur-xl group-hover:bg-accent4/20 transition-colors rounded-full" />
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                )}
            </div>

            <style>{`
                .custom-scrollbar::-webkit-scrollbar { width: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 4px; }
                .custom-scrollbar:hover::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); }
            `}</style>
        </div>
    );
}

function Skeleton() {
    return (
        <div className="h-20 rounded-xl bg-white/5 animate-pulse border border-white/10" />
    );
}
