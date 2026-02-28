import { useState, useEffect } from 'react';

type LinkItem = {
    url: string;
    total_count?: number;
    group_titles?: string;
    sender_names?: string;
    first_seen?: string;
    last_seen?: string;
    title?: string;
    description?: string;
    image_url?: string;
    tags?: string;
};

export function LinksPage() {
    const [links, setLinks] = useState<LinkItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [activeTag, setActiveTag] = useState<string | null>(null);

    useEffect(() => {
        fetch('/api/links?limit=50')
            .then(r => r.json())
            .then(d => setLinks(d.data || []))
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, []);

    const allTags = Array.from(new Set(links.map(l => l.tags).filter(Boolean))) as string[];
    const filteredLinks = activeTag ? links.filter(l => l.tags === activeTag) : links;

    return (
        <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden flex flex-col h-full">
            <div className="py-4 px-5 border-b border-border-subtle bg-white/[0.03] shrink-0">
                <div className="flex justify-between items-center mb-3">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5"><span>🔗</span> 全局链接聚合</h3>
                    <span className="text-[11px] text-text3 bg-bg-primary px-2 py-0.5 rounded-full border border-border-subtle">最近 50 条</span>
                </div>
                {allTags.length > 0 && (
                    <div className="flex flex-wrap gap-2">
                        <button
                            onClick={() => setActiveTag(null)}
                            className={`text-[11px] px-2.5 py-1 rounded-full transition-colors border ${activeTag === null ? 'bg-accent text-white border-accent' : 'bg-transparent text-text2 border-border-subtle hover:bg-white/[0.05]'}`}
                        >
                            全部
                        </button>
                        {allTags.map(tag => (
                            <button
                                key={tag}
                                onClick={() => setActiveTag(tag)}
                                className={`text-[11px] px-2.5 py-1 rounded-full transition-colors border ${activeTag === tag ? 'bg-accent text-white border-accent' : 'bg-transparent text-text2 border-border-subtle hover:bg-white/[0.05]'}`}
                            >
                                {tag}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-bg-primary/30">
                {isLoading ? (
                    <div className="p-5 text-center text-text3 text-[13px]">加载中...</div>
                ) : filteredLinks.length === 0 ? (
                    <div className="p-5 text-center text-text3 text-[13px]">暂无链接数据</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {filteredLinks.map((l, i) => (
                            <a
                                key={i}
                                href={l.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="group flex flex-col bg-bg-primary rounded-xl border border-border-subtle overflow-hidden hover:border-accent/40 hover:shadow-lg hover:shadow-accent/5 transition-all duration-300 transform hover:-translate-y-1"
                            >
                                {l.image_url ? (
                                    <div className="w-full h-32 overflow-hidden border-b border-border-subtle relative bg-black/10">
                                        <img src={l.image_url} alt="cover" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onError={(e) => (e.currentTarget.style.display = 'none')} />
                                        {l.tags && (
                                            <span className="absolute top-2 right-2 text-[10px] font-medium bg-black/60 backdrop-blur-md text-white px-2 py-1 rounded-md">
                                                {l.tags}
                                            </span>
                                        )}
                                    </div>
                                ) : (
                                    <div className="w-full h-2 min-h-2 bg-gradient-to-r from-accent/20 to-accent2/20"></div>
                                )}

                                <div className="p-4 flex-1 flex flex-col">
                                    {!l.image_url && l.tags && (
                                        <div className="mb-2">
                                            <span className="inline-block text-[10px] font-medium bg-accent/10 text-accent px-2 py-0.5 rounded-md border border-accent/20">
                                                {l.tags}
                                            </span>
                                        </div>
                                    )}

                                    <h4 className="text-[13px] font-medium text-text1 line-clamp-2 mb-1.5 group-hover:text-accent transition-colors">
                                        {l.title || l.url.replace(/^https?:\/\//, '').split('/')[0]}
                                    </h4>

                                    {l.description ? (
                                        <p className="text-[11px] text-text2 line-clamp-2 mb-3 flex-1">{l.description}</p>
                                    ) : (
                                        <div className="flex-1"></div>
                                    )}

                                    <div className="mt-auto pt-3 border-t border-border-subtle/50 flex flex-col gap-1.5">
                                        <div className="text-[10px] text-text3 flex items-center gap-1.5 break-all line-clamp-1">
                                            <span className="shrink-0">🔗</span> <span className="truncate">{l.url}</span>
                                        </div>
                                        <div className="flex items-center justify-between text-[10px] text-text3">
                                            <div className="flex items-center gap-1">
                                                <span className="w-2 h-2 rounded-full bg-accent2/50"></span>
                                                <span className="line-clamp-1">{l.group_titles?.split(',')[0]} {l.group_titles?.includes(',') && '...'}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {l.total_count && l.total_count > 1 && (
                                                    <span className="text-orange-400 font-medium">🔥 {l.total_count}次</span>
                                                )}
                                                <span>{l.last_seen?.split(' ')[1] || l.last_seen}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </a>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
