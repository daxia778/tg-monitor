import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

type StatCardsProps = {
    totalMessages: string | number;
    last24hMessages: string | number;
    alertKeyword: string | number;
    groupCount: string | number;
    aiModel: string;
};

// Hook for Number Counting Animation
function useCounter(targetValue: string | number, duration: number = 1000) {
    const [count, setCount] = useState<number | string>(0);

    useEffect(() => {
        if (typeof targetValue === 'string') {
            if (count !== targetValue) {
                 
                setCount(targetValue);
            }
            return;
        }

        let startTimestamp: number | null = null;
        const target = targetValue;

        const step = (timestamp: number) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);

            // easeOutQuart
            const easeProgress = 1 - Math.pow(1 - progress, 4);
            setCount(Math.floor(easeProgress * target));

            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                setCount(target);
            }
        };

        window.requestAnimationFrame(step);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [targetValue, duration]);

    return count;
}

export function StatCards({ totalMessages, last24hMessages, alertKeyword, groupCount, aiModel }: StatCardsProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6 relative z-10">
            <StatCard
                icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>
                }
                value={totalMessages}
                label="总抓取量"
                color="var(--color-accent4)"
            />
            <StatCard
                icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
                }
                value={last24hMessages}
                label="24h 增量"
                color="var(--color-accent)"
            />
            <StatCard
                icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                }
                value={alertKeyword}
                label="命中告警"
                color="var(--color-accent6)"
            />
            <StatCard
                icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" /></svg>
                }
                value={groupCount}
                label="活跃群组"
                color="var(--color-accent2)"
            />
            <StatCard
                icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                }
                value={aiModel}
                label="AI Core"
                color="var(--color-accent5)"
            />
        </div>
    );
}

function StatCard({ icon, value, label, color }: { icon: React.ReactNode; value: string | number; label: string; color: string }) {
    const displayValue = useCounter(value);

    return (
        <div className="glass-panel rounded-2xl p-5 relative group transition-all duration-300 hover:bg-bg-hover hover:-translate-y-1 hover:border-white/20 active:scale-[0.98]">
            <div className="flex items-center justify-between mb-4">
                <div className="text-text3 group-hover:text-text-main transition-colors duration-300">
                    {label}
                </div>
                <div className="p-2 rounded-lg bg-white/5 text-text-main border border-white/5 opacity-80 group-hover:opacity-100 group-hover:bg-white/10 transition-all duration-300">
                    <div style={{ color: color }}>{icon}</div>
                </div>
            </div>

            <div className="flex items-baseline gap-2">
                <motion.div
                    key={typeof displayValue === 'number' ? displayValue : String(displayValue)}
                    initial={{ scale: 1.1, color: '#22c55e', textShadow: '0 0 10px rgba(34, 197, 94, 0.5)' }}
                    animate={{ scale: 1, color: '#ffffff', textShadow: '0 0 0px rgba(255,255,255,0)' }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="text-3xl font-bold tracking-tight text-white font-mono shadow-white"
                >
                    {typeof value === 'number' || typeof value === 'string' && value !== '...' ? displayValue : '...'}
                </motion.div>
            </div>

            {/* Subtle glow effect underneath */}
            <div
                className="absolute -bottom-4 -right-4 w-24 h-24 blur-3xl rounded-full opacity-0 group-hover:opacity-20 transition-opacity duration-500 pointer-events-none"
                style={{ backgroundColor: color }}
            />
        </div>
    );
}
