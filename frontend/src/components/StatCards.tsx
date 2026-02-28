

type StatCardsProps = {
    totalMessages: string | number;
    last24hMessages: string | number;
    alertKeyword: string | number;
    groupCount: string | number;
    aiModel: string;
};

export function StatCards({ totalMessages, last24hMessages, alertKeyword, groupCount, aiModel }: StatCardsProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5 mb-5">
            <StatCard
                icon="📊"
                value={totalMessages}
                label="总抓取量"
                topColor="var(--color-accent)"
            />
            <StatCard
                icon="📉"
                value={last24hMessages}
                label="24h 增量"
                topColor="var(--color-accent4)"
            />
            <StatCard
                icon="⚠️"
                value={alertKeyword}
                label="命中间键词"
                topColor="var(--color-accent5)"
            />
            <StatCard
                icon="👥"
                value={groupCount}
                label="活跃群组"
                topColor="var(--color-accent3)"
            />
            <StatCard
                icon="⚡"
                value={aiModel}
                label="AI 摘要模型"
                topColor="var(--color-accent2)"
            />
        </div>
    );
}

function StatCard({ icon, value, label, topColor }: { icon: string; value: string | number; label: string; topColor: string }) {
    return (
        <div className="bg-bg-card rounded-[14px] p-4.5 border border-border-subtle relative overflow-hidden transition-transform duration-250 hover:-translate-y-[3px] cursor-pointer hover:shadow-[0_4px_24px_rgba(0,0,0,0.3)] hover:border-accent/20 active:scale-[0.97]">
            <div
                className="absolute top-0 left-0 w-full h-[2px]"
                style={{ backgroundColor: topColor }}
            ></div>
            <div className="text-[22px] mb-2">{icon}</div>
            <div className="text-[28px] font-bold tracking-tight">{value}</div>
            <div className="text-[12px] text-text2 mt-0.5">{label}</div>
        </div>
    );
}
