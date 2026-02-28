import { useState, useEffect } from 'react';

type AlertsConfig = {
    enabled: boolean;
    keywords: string[];
};

type LLMStatus = {
    url: string;
    model: string;
    keys_count: number;
    max_concurrent: number;
    test_status?: string;
};

export function SettingsPage() {
    const [alerts, setAlerts] = useState<AlertsConfig | null>(null);
    const [llm, setLlm] = useState<LLMStatus | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            fetch('/api/alerts/config').then(r => r.json()),
            fetch('/api/llm/status').then(r => r.json()),
        ])
            .then(([alertsData, llmData]) => {
                setAlerts(alertsData);
                setLlm(llmData);
            })
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, []);

    const handleToggleAlerts = async () => {
        if (!alerts) return;
        const newStatus = !alerts.enabled;

        try {
            const res = await fetch('/api/alerts/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: newStatus }),
            });
            const data = await res.json();
            if (res.ok && data.ok) {
                setAlerts({ ...alerts, enabled: newStatus });
            } else {
                alert(data.detail || '切换告警状态失败');
            }
        } catch (error) {
            console.error(error);
            alert('网络错误，无法连接后端');
        }
    };

    if (isLoading) {
        return <div className="p-5 text-center text-text3 text-[13px]">加载中...</div>;
    }

    return (
        <div className="space-y-6 max-w-3xl">
            <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
                <div className="py-4 px-5 border-b border-border-subtle bg-white/[0.03]">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5">
                        <span>⚙️</span> 基础设置
                    </h3>
                </div>
                <div className="p-5 space-y-4">
                    <div className="flex justify-between items-center py-2">
                        <div>
                            <div className="text-[13px] font-medium text-text-main">系统语言</div>
                            <div className="text-[11px] text-text3 mt-0.5">目前仅支持简体中文</div>
                        </div>
                        <div className="text-[13px] text-text2 bg-bg-secondary px-3 py-1.5 rounded-lg border border-border-subtle">
                            简体中文
                        </div>
                    </div>
                    <div className="h-px bg-border-subtle" />
                    <div className="flex justify-between items-center py-2">
                        <div>
                            <div className="text-[13px] font-medium text-text-main">主题偏好</div>
                            <div className="text-[11px] text-text3 mt-0.5">控制台主题外观</div>
                        </div>
                        <div className="text-[13px] text-accent font-medium bg-accent/10 px-3 py-1.5 rounded-lg border border-accent/20">
                            🌙 深色模式
                        </div>
                    </div>
                </div>
            </div>

            <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
                <div className="py-4 px-5 border-b border-border-subtle bg-white/[0.03]">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5">
                        <span>🤖</span> 大模型 (LLM) 代理配置
                    </h3>
                </div>
                <div className="p-5 space-y-4">
                    <div className="flex justify-between items-center py-2">
                        <div>
                            <div className="text-[13px] font-medium text-text-main">当前路由节点</div>
                            <div className="text-[11px] text-text3 mt-0.5">{llm?.url || '—'}</div>
                        </div>
                        <div className="text-[11px] text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                            正常连通
                        </div>
                    </div>
                    <div className="flex justify-between items-center py-2">
                        <div>
                            <div className="text-[13px] font-medium text-text-main">目标模型名称</div>
                            <div className="text-[11px] text-text3 mt-0.5">生成摘要所使用的基座模型</div>
                        </div>
                        <div className="text-[13px] text-text2 font-mono">
                            {llm?.model || 'gpt-5.3-codex'}
                        </div>
                    </div>
                    <div className="flex justify-between items-center py-2">
                        <div>
                            <div className="text-[13px] font-medium text-text-main">并发与通道池</div>
                            <div className="text-[11px] text-text3 mt-0.5">加载的下游 Key 数量及分发能力</div>
                        </div>
                        <div className="text-[12px] text-text2">
                            <span className="text-accent2 font-bold">{llm?.keys_count || 0}</span> 个通道 / 最大并发: <span className="text-accent2 font-bold">{llm?.max_concurrent || 10}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div className={`bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden transition-opacity duration-300 ${!alerts?.enabled ? 'opacity-70' : ''}`}>
                <div className="py-4 px-5 border-b border-border-subtle bg-white/[0.03] flex justify-between items-center">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5">
                        <span className="text-red-400">⚠️</span> 关键词告警 (Bot 推送)
                    </h3>
                    <button
                        onClick={handleToggleAlerts}
                        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors duration-200 ease-in-out focus:outline-none ${alerts?.enabled ? 'bg-accent' : 'bg-white/10'}`}
                    >
                        <span className="sr-only">开关告警</span>
                        <span aria-hidden="true" className={`pointer-events-none inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${alerts?.enabled ? 'translate-x-1.5' : '-translate-x-1.5'}`} />
                    </button>
                </div>
                <div className="p-5">
                    <div className="flex justify-between items-center mb-4">
                        <div className="text-[13px] font-medium text-text-main">
                            消息内容实时告警
                        </div>
                        <div className={`text-[11px] px-2 py-0.5 rounded-full border ${alerts?.enabled ? 'text-green-400 bg-green-500/10 border-green-500/20' : 'text-text3 bg-white/5 border-white/10'}`}>
                            {alerts?.enabled ? '已开启' : '已关闭'}
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {alerts?.keywords?.map(kw => (
                            <span key={kw} className="text-[11px] px-2.5 py-1 bg-bg-secondary text-text3 rounded-lg border border-border-subtle">
                                {kw}
                            </span>
                        ))}
                        {!alerts?.keywords?.length && <span className="text-[12px] text-text3">未配置告警词</span>}
                    </div>

                    <div className="text-[11px] text-text3 mt-4 leading-relaxed">
                        * 提示: 开启此功能后，包含以上关键词的群组消息将会通过 Telegram Bot 实时推送到您的私聊频道。如果触发过于频繁，建议将其关闭并仅依赖定期生成的摘要报告。
                    </div>
                </div>
            </div>
        </div>
    );
}
