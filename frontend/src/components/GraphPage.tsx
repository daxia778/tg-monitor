import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, MessageSquare, Zap, Crown, ArrowUpRight } from 'lucide-react';

type NodeData = {
    id: number;
    name: string;
    msg_count: number;
    reply_received: number;
    forward_received: number;
    kol_score: number;
    groups: string;
};

type HeatmapData = {
    weekday: number;
    hour: number;
    count: number;
};

export function GraphPage() {
    const [activeTab, setActiveTab] = useState<'leaderboard' | 'heatmap'>('leaderboard');

    // Nodes
    const [nodes, setNodes] = useState<NodeData[]>([]);
    // Heatmap
    const [heatmap, setHeatmap] = useState<HeatmapData[]>([]);

    // Status
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;
        setLoading(true);

        Promise.all([
            fetch('/api/graph/nodes?limit=100').then(r => r.json()),
            fetch('/api/graph/heatmap').then(r => r.json())
        ]).then(([nodesData, heatData]) => {
            if (!isMounted) return;
            setNodes(nodesData.nodes || []);
            setHeatmap(heatData.matrix || []);
        }).catch(err => console.error("Failed to load graph data", err))
            .finally(() => { if (isMounted) setLoading(false); });

        return () => { isMounted = false; };
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center p-20 h-full">
                <div className="flex gap-2">
                    <div className="w-3 h-3 bg-white/20 rounded-full animate-bounce" />
                    <div className="w-3 h-3 bg-white/40 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                    <div className="w-3 h-3 bg-white/60 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-120px)] overflow-hidden gap-6">
            {/* Header Tabs */}
            <div className="flex items-center gap-2">
                <button
                    onClick={() => setActiveTab('leaderboard')}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-semibold transition-all ${activeTab === 'leaderboard'
                        ? 'bg-white text-black shadow-[0_4px_20px_rgba(255,255,255,0.3)]'
                        : 'bg-white/5 text-text2 hover:bg-white/10 hover:text-white'
                        }`}
                >
                    <Crown className="w-4 h-4" />
                    KOL 排行榜
                </button>
                <button
                    onClick={() => setActiveTab('heatmap')}
                    className={`flex items-center gap-2 px-6 py-2.5 rounded-full text-sm font-semibold transition-all ${activeTab === 'heatmap'
                        ? 'bg-white text-black shadow-[0_4px_20px_rgba(255,255,255,0.3)]'
                        : 'bg-white/5 text-text2 hover:bg-white/10 hover:text-white'
                        }`}
                >
                    <Activity className="w-4 h-4" />
                    全局活跃热力图
                </button>
            </div>

            {/* Content Area */}
            <div className="flex-1 relative glass-panel rounded-3xl border border-white/10 overflow-hidden flex flex-col p-6">

                {/* ─── TAB 1: KOL 排行榜 ─── */}
                {activeTab === 'leaderboard' && (
                    <div className="flex-1 flex flex-col h-full overflow-hidden">
                        <div className="flex items-center justify-between mb-6 px-2">
                            <h2 className="text-xl font-bold flex items-center gap-2">
                                <span className="w-2 h-6 bg-accent4 rounded-full" />
                                意见领袖 (KOL) 核心影响谱带
                            </h2>
                            <p className="text-sm text-text3">根据 发言量(1x) + 收到的回复(3x) + 被转发(2x) 综合测算得出</p>
                        </div>

                        <div className="flex-1 overflow-y-auto custom-scrollbar px-2 pb-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                                <AnimatePresence mode="popLayout">
                                    {nodes.slice(0, 30).map((node, i) => {
                                        // Top 3 gets special styling
                                        const isTop3 = i < 3;

                                        return (
                                            <motion.div
                                                key={node.id}
                                                initial={{ opacity: 0, y: 20 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.03 }}
                                                className={`relative rounded-2xl p-5 border transition-all hover:-translate-y-1 ${isTop3
                                                    ? 'bg-gradient-to-br from-white/10 to-transparent border-white/30 shadow-[0_8px_30px_rgba(255,255,255,0.05)]'
                                                    : 'bg-black/40 border-white/10 hover:border-white/20 hover:bg-white/5'
                                                    }`}
                                            >
                                                {/* Rank Badge */}
                                                <div className={`absolute -top-3 -right-3 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-lg ${i === 0 ? 'bg-yellow-400 text-black shadow-yellow-400/50' :
                                                    i === 1 ? 'bg-zinc-300 text-black shadow-white/30' :
                                                        i === 2 ? 'bg-amber-600 text-white shadow-amber-600/30' :
                                                            'bg-black text-text3 border border-white/10'
                                                    }`}>
                                                    #{i + 1}
                                                </div>

                                                <div className="flex items-start justify-between mb-4">
                                                    <div>
                                                        <h3 className="text-lg font-bold text-white mb-1 flex items-center gap-2 truncate max-w-[200px]" title={node.name}>
                                                            {node.name}
                                                        </h3>
                                                        <div className="text-xs text-text3 truncate max-w-[200px]" title={node.groups}>
                                                            活跃于: {node.groups.split(',').slice(0, 2).join(', ')} {node.groups.split(',').length > 2 && '...'}
                                                        </div>
                                                    </div>

                                                    {/* Score */}
                                                    <div className="text-right">
                                                        <div className="text-[10px] text-accent4 font-bold uppercase tracking-wider mb-0.5">影响力分值</div>
                                                        <div className={`text-2xl font-black ${isTop3 ? 'text-white' : 'text-text2'}`}>
                                                            {node.kol_score.toLocaleString()}
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="grid grid-cols-3 gap-2 mt-auto">
                                                    <div className="bg-black/50 rounded-lg p-2.5 flex flex-col items-center justify-center border border-white/5">
                                                        <MessageSquare className="w-3 h-3 text-text3 mb-1" />
                                                        <span className="text-xs font-mono">{node.msg_count}</span>
                                                        <span className="text-[10px] text-text3 transform scale-90">发言</span>
                                                    </div>
                                                    <div className="bg-black/50 rounded-lg p-2.5 flex flex-col items-center justify-center border border-white/5">
                                                        <ArrowUpRight className="w-3 h-3 text-green-400 mb-1" />
                                                        <span className="text-xs font-mono">{node.reply_received}</span>
                                                        <span className="text-[10px] text-text3 transform scale-90">被回复</span>
                                                    </div>
                                                    <div className="bg-black/50 rounded-lg p-2.5 flex flex-col items-center justify-center border border-white/5">
                                                        <Zap className="w-3 h-3 text-orange-400 mb-1" />
                                                        <span className="text-xs font-mono">{node.forward_received}</span>
                                                        <span className="text-[10px] text-text3 transform scale-90">被转发</span>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </AnimatePresence>
                            </div>
                        </div>
                    </div>
                )}


                {/* ─── TAB 2: 热力图 ─── */}
                {activeTab === 'heatmap' && (
                    <HeatmapRenderer matrix={heatmap} />
                )}

            </div>
        </div>
    );
}

// ============== Helper Component for Heatmap ==============

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

function HeatmapRenderer({ matrix }: { matrix: HeatmapData[] }) {
    // We want to render a grid where Y is weekday (0-6) and X is hour (0-23)

    // Create a 7x24 map filled with 0
    const heatMapArray = Array.from({ length: 7 }, () => Array(24).fill(0));
    let maxVal = 1;

    matrix.forEach(d => {
        heatMapArray[d.weekday][d.hour] = d.count;
        if (d.count > maxVal) maxVal = d.count;
    });

    const getColor = (count: number) => {
        if (count === 0) return 'rgba(255, 255, 255, 0.02)';
        const ratio = count / maxVal;

        // Github contribution-like colors, but cyberpunk blue/purple
        if (ratio < 0.2) return 'rgba(14, 165, 233, 0.2)'; // Very light cyber blue
        if (ratio < 0.4) return 'rgba(14, 165, 233, 0.4)';
        if (ratio < 0.6) return 'rgba(139, 92, 246, 0.6)'; // Purple start
        if (ratio < 0.8) return 'rgba(139, 92, 246, 0.8)';
        return 'rgba(239, 68, 68, 0.9)'; // Red/Pink hotspot
    };

    return (
        <div className="flex-1 flex flex-col items-center justify-center p-4">
            <h2 className="text-xl font-bold mb-8 text-white w-full text-center">群聊活跃度聚合矩阵 (最后 60 天)</h2>

            <div className="flex flex-col gap-2 p-6 bg-black/40 rounded-[28px] border border-white/10 shadow-2xl overflow-x-auto w-full max-w-5xl">

                {/* Hours Header */}
                <div className="flex gap-2 pl-12">
                    {Array.from({ length: 24 }).map((_, h) => (
                        <div key={h} className="w-6 md:w-8 h-4 flex items-center justify-center text-[10px] text-text3">
                            {h % 2 === 0 ? h : ''}
                        </div>
                    ))}
                </div>

                {/* Heatmap Body */}
                {WEEKDAYS.map((day, dIdx) => (
                    <div key={day} className="flex gap-2 items-center">
                        <div className="w-10 text-xs text-text2 font-medium text-right shrink-0">{day}</div>
                        {Array.from({ length: 24 }).map((_, hIdx) => {
                            const val = heatMapArray[dIdx][hIdx];
                            const ms = hIdx * 20 + dIdx * 50; // Staggered animation delay

                            return (
                                <motion.div
                                    key={`${dIdx}-${hIdx}`}
                                    initial={{ opacity: 0, scale: 0.5 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ delay: ms / 1000, duration: 0.3 }}
                                    className="w-6 h-6 md:w-8 md:h-8 rounded-sm transition-all hover:scale-125 cursor-crosshair group relative"
                                    style={{ backgroundColor: getColor(val) }}
                                >
                                    {/* Tooltip */}
                                    {val > 0 && (
                                        <div className="absolute opacity-0 group-hover:opacity-100 bottom-full left-1/2 -translate-x-1/2 -translate-y-2 bg-white text-black text-[10px] font-bold py-1 px-2 rounded pointer-events-none whitespace-nowrap z-50 transition-opacity">
                                            {day} {hIdx}点: {val} 条讯息
                                        </div>
                                    )}
                                </motion.div>
                            )
                        })}
                    </div>
                ))}
            </div>

            <div className="mt-8 flex items-center justify-center gap-4 text-xs text-text3">
                <span>消息少</span>
                <div className="flex gap-1.5">
                    <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: 'rgba(255, 255, 255, 0.02)' }} />
                    <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: 'rgba(14, 165, 233, 0.2)' }} />
                    <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: 'rgba(14, 165, 233, 0.4)' }} />
                    <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: 'rgba(139, 92, 246, 0.6)' }} />
                    <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: 'rgba(139, 92, 246, 0.8)' }} />
                    <div className="w-4 h-4 rounded-sm" style={{ backgroundColor: 'rgba(239, 68, 68, 0.9)' }} />
                </div>
                <span>信息洪峰</span>
            </div>
        </div>
    )
}
