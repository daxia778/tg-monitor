import { useMemo } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function CyberCharts() {
    // Generate mock 24h data with a cyber glow vibe
    const data = useMemo(() => {
        const now = new Date();
        const res = [];
        for (let i = 24; i >= 0; i--) {
            const t = new Date(now.getTime() - i * 60 * 60 * 1000);
            res.push({
                time: `${t.getHours().toString().padStart(2, '0')}:00`,
                volume: Math.floor(Math.random() * 200 + 50) + (i === 12 || i === 4 ? 300 : 0), // some peaks
                alerts: Math.floor(Math.random() * 20)
            });
        }
        return res;
    }, []);

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="glass-panel p-3 rounded-xl border border-white/10 shadow-[0_0_15px_rgba(139,92,246,0.3)] bg-black/80 backdrop-blur-md">
                    <div className="text-text3 text-xs mb-2 font-mono">{label}</div>
                    <div className="text-accent4 text-sm font-semibold flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-accent4 glow-ai"></span>
                        流量: {payload[0].value} 条
                    </div>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="w-full glass-panel rounded-2xl p-5 md:p-6 mb-6 relative overflow-hidden group">
            <div className="flex justify-between items-center mb-6 relative z-10">
                <div>
                    <h3 className="text-base font-bold text-white flex items-center gap-2">
                        <span className="text-accent4">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                        </span>
                        态势折线图 (24H Traffic)
                    </h3>
                    <div className="text-xs text-text3 mt-1">全网消息流量洪峰监控</div>
                </div>
                <div className="flex items-center gap-2">
                    <span className="flex items-center gap-1.5 text-[10px] text-text3 bg-white/5 px-2 py-1 rounded-full border border-white/5">
                        <div className="w-1.5 h-1.5 rounded-full bg-accent4 animate-pulse"></div>
                        Live
                    </span>
                </div>
            </div>

            <div className="h-[200px] md:h-[240px] w-full relative z-10">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.5} />
                                <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                            </linearGradient>
                            {/* Deep blue bottom glow effect implementation */}
                            <filter id="glow">
                                <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                                <feMerge>
                                    <feMergeNode in="coloredBlur" />
                                    <feMergeNode in="SourceGraphic" />
                                </feMerge>
                            </filter>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                        <XAxis
                            dataKey="time"
                            stroke="rgba(255,255,255,0.2)"
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                            tickLine={false}
                            axisLine={false}
                            minTickGap={30}
                        />
                        <YAxis
                            stroke="rgba(255,255,255,0.2)"
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                        <Area
                            type="monotone"
                            dataKey="volume"
                            stroke="#0ea5e9"
                            strokeWidth={3}
                            fillOpacity={1}
                            fill="url(#colorVolume)"
                            activeDot={{ r: 6, fill: '#0ea5e9', stroke: '#000', strokeWidth: 2, filter: 'url(#glow)' }}
                            style={{ filter: 'drop-shadow(0 0 10px rgba(14,165,233,0.5))' }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            {/* Decorative background glow */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-accent4/5 blur-[100px] pointer-events-none rounded-full opacity-50 group-hover:opacity-100 transition-opacity duration-700" />
        </div>
    );
}
