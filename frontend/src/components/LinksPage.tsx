import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link2, Flame, Calendar, Hash, Globe } from 'lucide-react';

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
    const [activeDomain, setActiveDomain] = useState<string | null>(null);

    useEffect(() => {
        fetch('/api/links?limit=200') // fetch more to group them
            .then(r => r.json())
            .then(d => setLinks(d.data || []))
            .catch(console.error)
            .finally(() => setIsLoading(false));
    }, []);

    // Process and group links
    const { groupedLinks, domains } = useMemo(() => {
        // We will group by URL to aggregate counts if they aren't already grouped by backend
        const map = new Map<string, LinkItem>();

        links.forEach(link => {
            // Normalize: remove http/https, remove trailing slash, and remove query params
            const cleanUrl = link.url.split('?')[0].replace(/^https?:\/\//, '').replace(/\/$/, '');

            if (map.has(cleanUrl)) {
                const existing = map.get(cleanUrl)!;
                existing.total_count = (existing.total_count || 1) + (link.total_count || 1);
            } else {
                // Store a cleaner version of the URL for display
                map.set(cleanUrl, { ...link, url: link.url.split('?')[0], total_count: link.total_count || 1 });
            }
        });

        const merged = Array.from(map.values())
            .sort((a, b) => (b.total_count || 0) - (a.total_count || 0));

        // Format domains for filtering
        const rawDomains = merged.map(l => {
            try { return new URL(l.url.startsWith('http') ? l.url : `https://${l.url}`).hostname; } catch { return 'other'; }
        });

        // Count top domains
        const domainCounts = rawDomains.reduce((acc, domain) => {
            acc[domain] = (acc[domain] || 0) + 1;
            return acc;
        }, {} as Record<string, number>);

        // Get top 5 domains that have more than 1 link
        const topDomains = Object.entries(domainCounts)
            .filter(([_, count]) => count > 1)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([domain]) => domain);

        return { groupedLinks: merged, domains: topDomains };
    }, [links]);

    // Filter
    const displayLinks = activeDomain
        ? groupedLinks.filter(l => {
            try {
                const hostname = new URL(l.url.startsWith('http') ? l.url : `https://${l.url}`).hostname;
                return hostname === activeDomain;
            } catch { return false; }
        })
        : groupedLinks;

    if (isLoading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6].map(i => (
                    <div key={i} className="h-40 rounded-3xl bg-white/[0.03] animate-pulse border border-white/30" />
                ))}
            </div>
        );
    }

    if (groupedLinks.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-20 glass-panel rounded-3xl border border-white/30 h-full">
                <Link2 className="w-16 h-16 text-text3 mb-4 opacity-50" />
                <div className="text-text2 font-medium">暂时没有捕获到链接数据</div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-[calc(100vh-120px)]">
            {/* Minimalist Top Filter Bar */}
            <div className="flex items-center gap-4 mb-8 flex-wrap">
                <button
                    onClick={() => setActiveDomain(null)}
                    className={`px-5 py-2 rounded-full text-[13px] font-bold border transition-all shadow-sm tracking-wide ${activeDomain === null
                        ? 'bg-white text-black border-white shadow-[0_4px_15px_rgba(255,255,255,0.4)]'
                        : 'bg-black/60 text-text2 border-white/30 hover:border-white/50 hover:text-white hover:bg-black/80'
                        }`}
                >
                    全部集合 ({groupedLinks.length})
                </button>

                {domains.map(domain => (
                    <button
                        key={domain}
                        onClick={() => setActiveDomain(domain)}
                        className={`flex items-center gap-1.5 px-5 py-2 rounded-full text-[13px] font-bold border transition-all shadow-sm tracking-wide ${activeDomain === domain
                            ? 'bg-white text-black border-white shadow-[0_4px_15px_rgba(255,255,255,0.4)]'
                            : 'bg-black/60 text-text2 border-white/30 hover:border-white/50 hover:text-white hover:bg-black/80'
                            }`}
                    >
                        <Globe className="w-3.5 h-3.5" />
                        {domain}
                    </button>
                ))}
            </div>

            {/* Grid display focusing on URL styling and frequency */}
            <div className="flex-1 overflow-y-auto custom-scrollbar pb-10 px-1">
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 lg:gap-6">
                    <AnimatePresence mode="popLayout">
                        {displayLinks.map((link, idx) => {
                            let domain = 'unknown';
                            try { domain = new URL(link.url.startsWith('http') ? link.url : `https://${link.url}`).hostname; } catch { }

                            return (
                                <motion.a
                                    key={link.url}
                                    href={link.url.startsWith('http') ? link.url : `https://${link.url}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    initial={{ opacity: 0, scale: 0.95, y: 15 }}
                                    animate={{ opacity: 1, scale: 1, y: 0 }}
                                    exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.1 } }}
                                    transition={{ delay: Math.min(idx * 0.04, 0.4), type: 'spring', stiffness: 300, damping: 25 }}
                                    className="group relative glass-panel rounded-[24px] border border-white/30 bg-black/60 hover:bg-black/40 hover:-translate-y-1 transition-all duration-300 overflow-hidden flex flex-col shadow-lg hover:shadow-[0_8px_30px_rgba(255,255,255,0.15)] hover:border-white/60"
                                >
                                    {/* White stroke outline effect on hover */}
                                    <div className="absolute inset-0 border-2 border-transparent group-hover:border-white/40 rounded-[24px] transition-colors pointer-events-none z-20" />

                                    {/* Subtitle Glow based on heat */}
                                    {(link.total_count || 0) > 10 && (
                                        <div className="absolute -top-10 -right-10 w-32 h-32 bg-orange-500/20 blur-3xl group-hover:bg-orange-500/30 transition-colors pointer-events-none rounded-full z-0" />
                                    )}

                                    <div className="p-5 flex-1 flex flex-col relative z-10">
                                        <div className="flex justify-between items-start mb-4">
                                            <div className="bg-white/5 px-3 py-1 rounded-lg border border-white/10 flex items-center gap-2">
                                                <Globe className="w-3.5 h-3.5 text-text3" />
                                                <span className="text-xs font-mono font-medium text-text2 truncate max-w-[150px]">{domain}</span>
                                            </div>

                                            <div className="flex items-center gap-1.5 bg-black/50 px-3 py-1 rounded-full border border-orange-500/30 shadow-[0_0_10px_rgba(249,115,22,0.1)]">
                                                <Flame className={`w-3.5 h-3.5 ${(link.total_count || 0) > 5 ? 'text-orange-500' : 'text-orange-300'}`} />
                                                <span className="text-xs font-bold text-orange-400">{link.total_count || 1} 次</span>
                                            </div>
                                        </div>

                                        <h4 className="text-[14px] font-semibold text-white leading-tight mb-2 group-hover:text-accent4 transition-colors break-words">
                                            {link.url}
                                        </h4>

                                        <div className="mt-auto pt-4 flex items-center justify-between text-[11px] text-text3">
                                            <div className="flex items-center gap-1.5">
                                                <Hash className="w-3.5 h-3.5" />
                                                <span className="truncate max-w-[120px]">{link.group_titles?.split(',')[0]}</span>
                                            </div>
                                            <div className="flex items-center gap-1.5 font-mono">
                                                <Calendar className="w-3.5 h-3.5" />
                                                <span>{link.last_seen ? link.last_seen.slice(5, 16) : 'N/A'}</span>
                                            </div>
                                        </div>
                                    </div>
                                </motion.a>
                            );
                        })}
                    </AnimatePresence>
                </div>
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
