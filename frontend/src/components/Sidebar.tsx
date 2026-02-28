import { motion } from 'framer-motion';

interface SidebarProps {
    activeItem: string;
    onNavigate: (page: string) => void;
}

const NAV_ITEMS = [
    { id: 'dashboard', icon: '📊', label: '实时大盘' },
    { id: 'groups', icon: '👥', label: '群组监控' },
    { id: 'search', icon: '🔍', label: '全库搜索' },
    { id: 'chat', icon: '🤖', label: '私人智库' },
    { id: 'summaries', icon: '📝', label: '所有摘要' },
    { id: 'links', icon: '🔗', label: '链接收集' },
    { id: 'graph', icon: '🕸️', label: '关系图谱' },
    { id: 'accounts', icon: '🪪', label: '账号管理' },
];

export function Sidebar({ activeItem, onNavigate }: SidebarProps) {
    return (
        <aside className="w-[220px] bg-bg-sidebar backdrop-blur-md border-r border-border-subtle h-screen fixed top-0 left-0 z-[200] flex flex-col">
            <div className="p-5 border-b border-border-subtle flex items-center gap-2.5 select-none">
                <span className="text-xl">🔍</span>
                <h1 className="text-base text-accent font-bold">TG Monitor</h1>
            </div>

            <nav className="flex-1 p-3 overflow-y-auto space-y-0.5 relative">
                {NAV_ITEMS.map(item => {
                    const isActive = activeItem === item.id;
                    return (
                        <button
                            key={item.id}
                            id={`nav-${item.id}`}
                            onClick={() => onNavigate(item.id)}
                            className={`relative w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-[13px] font-medium transition-colors duration-200 text-left cursor-pointer border-0 ${isActive
                                ? 'text-accent'
                                : 'text-text2 bg-transparent hover:text-text-main hover:bg-white/5'
                                }`}
                        >
                            {isActive && (
                                <motion.div
                                    layoutId="sidebar-active-indicator"
                                    className="absolute inset-0 bg-white/10 rounded-lg border-l-[3px] border-accent"
                                    initial={false}
                                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                />
                            )}
                            <span className="relative z-10 text-base w-5 text-center">{item.icon}</span>
                            <span className="relative z-10">{item.label}</span>
                        </button>
                    );
                })}

                <div className="h-px bg-border-subtle my-2.5 mx-3.5" />

                <button
                    id="nav-settings"
                    onClick={() => onNavigate('settings')}
                    className={`relative w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-lg text-[13px] font-medium transition-colors duration-200 text-left cursor-pointer border-0 ${activeItem === 'settings'
                        ? 'text-accent'
                        : 'text-text2 bg-transparent hover:text-text-main hover:bg-white/5'
                        }`}
                >
                    {activeItem === 'settings' && (
                        <motion.div
                            layoutId="sidebar-active-indicator"
                            className="absolute inset-0 bg-white/10 rounded-lg border-l-[3px] border-accent"
                            initial={false}
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        />
                    )}
                    <span className="relative z-10 text-base w-5 text-center">⚙️</span>
                    <span className="relative z-10">偏好设置</span>
                </button>
            </nav>

            <div className="p-3.5 border-t border-border-subtle">
                <div className="flex items-center gap-1.5 text-xs text-accent4">
                    <div className="w-1.5 h-1.5 bg-accent4 rounded-full animate-pulse" />
                    监听中 (Collector)
                </div>
            </div>
        </aside>
    );
}
