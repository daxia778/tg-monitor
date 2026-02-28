import { useState, useEffect } from 'react';

type LinkItem = {
    url: string;
    text?: string;
    sender_name?: string;
    group_title?: string;
    date: string;
};

export function LinksPage() {
    const [links, setLinks] = useState<LinkItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        fetch('/api/links?limit=50')
            .then(r => r.json())
            .then(d => setLinks(d.data || []))
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, []);

    return (
        <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
            <div className="py-4 px-5 border-b border-border-subtle flex justify-between items-center bg-white/[0.03]">
                <h3 className="text-sm font-semibold flex items-center gap-1.5"><span>🔗</span> 最新分享链接</h3>
                <span className="text-[11px] text-text3 bg-bg-primary px-2 py-0.5 rounded-full border border-border-subtle">最近 50 条</span>
            </div>
            <div className="divide-y divide-border-subtle max-h-[700px] overflow-y-auto">
                {isLoading ? (
                    <div className="p-5 text-center text-text3 text-[13px]">加载中...</div>
                ) : links.length === 0 ? (
                    <div className="p-5 text-center text-text3 text-[13px]">暂无链接数据</div>
                ) : (
                    links.map((l, i) => (
                        <div key={i} className="px-5 py-3 hover:bg-white/[0.02] transition-colors">
                            <a
                                href={l.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[12px] text-accent hover:underline break-all"
                            >
                                {l.url}
                            </a>
                            {l.text && (
                                <div className="text-[11px] text-text2 mt-0.5 line-clamp-1">{l.text}</div>
                            )}
                            <div className="flex gap-2 mt-1 flex-wrap">
                                {l.group_title && (
                                    <span className="text-[10px] text-accent2">{l.group_title}</span>
                                )}
                                {l.sender_name && (
                                    <span className="text-[10px] text-text3">{l.sender_name}</span>
                                )}
                                <span className="text-[10px] text-text3">{l.date}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
