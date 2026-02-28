import { useState } from 'react';
import type { Message } from './MessageList';

export function SearchPage() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Message[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searched, setSearched] = useState(false);

    const doSearch = async () => {
        if (!query.trim()) return;
        setIsSearching(true);
        setSearched(true);
        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=100`);
            if (res.ok) {
                const data = await res.json();
                setResults(data.data || []);
            }
        } catch (e) {
            console.error('Search failed:', e);
        } finally {
            setIsSearching(false);
        }
    };

    return (
        <div>
            <div className="flex gap-2.5 mb-5">
                <input
                    id="search-input"
                    type="text"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && doSearch()}
                    placeholder="搜索消息内容、关键词..."
                    className="flex-1 bg-bg-secondary border border-border-subtle text-text-main px-4 py-2.5 rounded-xl text-[13px] outline-none focus:border-accent transition-colors placeholder:text-text3"
                />
                <button
                    id="btn-search"
                    onClick={doSearch}
                    disabled={isSearching}
                    className="bg-accent text-white px-5 py-2.5 rounded-xl text-[13px] font-medium cursor-pointer hover:opacity-85 transition-opacity active:scale-95 disabled:opacity-60"
                >
                    {isSearching ? '搜索中...' : '🔍 搜索'}
                </button>
            </div>

            {searched && (
                <div className="bg-bg-card rounded-[14px] border border-border-subtle overflow-hidden">
                    <div className="py-3.5 px-5 border-b border-border-subtle bg-white/[0.03] flex justify-between items-center">
                        <span className="text-sm font-semibold">搜索结果</span>
                        <span className="text-[11px] text-text3">{results.length} 条匹配</span>
                    </div>
                    {isSearching ? (
                        <div className="p-5 text-center text-text3 text-[13px]">搜索中...</div>
                    ) : results.length === 0 ? (
                        <div className="p-5 text-center text-text3 text-[13px]">未找到相关消息</div>
                    ) : (
                        <div className="divide-y divide-border-subtle max-h-[600px] overflow-y-auto">
                            {results.map((msg, i) => (
                                <div key={i} className="px-5 py-3 hover:bg-white/[0.02] transition-colors">
                                    <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                                        <span className="text-[10px] text-text3 font-mono">{msg.date}</span>
                                        {msg.group_title && (
                                            <span className="text-[10px] text-accent2 px-1.5 py-px bg-accent2/10 rounded-full">{msg.group_title}</span>
                                        )}
                                        <span className="text-[11px] text-accent font-medium">{msg.sender_name}</span>
                                    </div>
                                    <div className="text-xs text-text2 leading-relaxed break-words">
                                        {msg.text || <span className="text-text3 italic">[媒体文件]</span>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
