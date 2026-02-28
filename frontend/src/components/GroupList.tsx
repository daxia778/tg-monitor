
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
        <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
            <div className="py-4 px-5 border-b border-border-subtle flex justify-between items-center bg-white/[0.03]">
                <h3 className="text-sm font-semibold flex items-center gap-1.5">
                    <span>🔥</span> 活跃群组
                </h3>
                <span className="text-[11px] text-text3 bg-bg-primary px-2 py-0.5 rounded-full border border-border-subtle">
                    Top 10
                </span>
            </div>
            <div className="p-4 px-5">
                {isLoading ? (
                    <><Skeleton /><Skeleton /><Skeleton /></>
                ) : groups.length === 0 ? (
                    <div className="text-center text-text3 py-4 text-[13px]">暂无数据</div>
                ) : (
                    groups.map(g => (
                        <div
                            key={g.group_id}
                            className="flex justify-between items-center py-2.5 border-b border-border-subtle last:border-0 transition-colors hover:bg-glass hover:-mx-2 hover:px-2 rounded cursor-pointer"
                        >
                            <div className="flex-1 min-w-0 pr-4">
                                <div className="text-[13px] font-medium truncate text-text-main">{g.title}</div>
                                <div className="text-[10px] text-text3 mt-0.5">
                                    {g.message_count.toLocaleString()} 消息 · {g.active_users} 活跃用户
                                </div>
                                <div className="h-[2px] bg-accent/10 rounded-sm mt-1.5 overflow-hidden">
                                    <div
                                        className="h-full bg-accent rounded-sm transition-all duration-700"
                                        style={{ width: `${Math.min(100, (g.message_count / maxCount) * 100)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="text-sm font-bold text-accent whitespace-nowrap">
                                {g.message_count.toLocaleString()}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

function Skeleton() {
    return (
        <div className="h-14 rounded-xl bg-gradient-to-r from-white/[0.03] via-white/[0.07] to-white/[0.03] animate-pulse my-2 border border-border-subtle" />
    );
}
