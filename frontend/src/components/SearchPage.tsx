import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, CornerDownLeft, Sparkles } from 'lucide-react';
import type { Message } from './MessageList';

export function SearchPage() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Message[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [searched, setSearched] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Auto focus on mount
    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    // Global Cmd+K / Ctrl+K listener inside this page to re-focus
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                inputRef.current?.focus();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

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

    // Highlight neon keyword matching
    const highlightNeon = (text: string, keyword: string) => {
        if (!text) return <span className="text-text3 italic">[媒体文件]</span>;
        if (!keyword) return text;

        const parts = text.split(new RegExp(`(${keyword})`, 'gi'));
        return (
            <>
                {parts.map((part, i) =>
                    part.toLowerCase() === keyword.toLowerCase()
                        ? <span key={i} className="text-accent4 bg-accent4/10 px-1 rounded-md font-semibold [text-shadow:0_0_8px_rgba(14,165,233,0.5)]">{part}</span>
                        : part
                )}
            </>
        );
    };

    return (
        <div className="flex flex-col items-center pt-10 h-full">
            <motion.div
                initial={{ scale: 0.95, opacity: 0, y: -20 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
                className="w-full max-w-3xl glass-panel rounded-2xl overflow-hidden shadow-2xl border border-white/10 relative"
            >
                {/* Search Header */}
                <div className="flex items-center px-4 py-4 border-b border-white/10 bg-black/40 relative z-10">
                    <Search className="w-6 h-6 text-text3 mr-3" />
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && doSearch()}
                        placeholder="输入全库关键词追踪..."
                        className="flex-1 bg-transparent border-none text-white text-lg outline-none placeholder:text-text3/80 font-medium"
                    />
                    <div className="flex items-center gap-2 text-text3 text-xs bg-white/5 px-2 py-1 rounded-md border border-white/5">
                        <Command className="w-3.5 h-3.5" />
                        <span>K</span>
                    </div>
                </div>

                {/* Progress / Sparkles */}
                {isSearching && (
                    <div className="absolute top-0 left-0 w-full h-[2px] bg-transparent z-20 overflow-hidden">
                        <div className="h-full bg-accent4 w-1/3 animate-[shimmer_1s_infinite_ease-in-out] shadow-[0_0_10px_#0ea5e9]" />
                    </div>
                )}

                {/* Results Area */}
                <div className="bg-black/20 min-h-[100px] max-h-[60vh] overflow-y-auto w-full flex flex-col relative z-0">
                    <AnimatePresence mode="popLayout">
                        {!searched && !isSearching && (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="flex-1 flex flex-col items-center justify-center py-20 text-text3"
                            >
                                <Sparkles className="w-10 h-10 mb-4 opacity-50 text-accent5" />
                                <p className="text-sm">支持全局高斯模糊搜索，回车立即追踪全网情报</p>
                            </motion.div>
                        )}

                        {searched && (
                            <motion.div
                                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                                className="w-full"
                            >
                                <div className="px-5 py-3 text-xs font-semibold text-text3 bg-black/40 border-b border-white/5 uppercase tracking-wider sticky top-0 backdrop-blur-md z-10 flex justify-between">
                                    <span>Search Results</span>
                                    <span>{results.length} results</span>
                                </div>

                                {results.length === 0 && !isSearching ? (
                                    <div className="py-20 text-center text-text3 text-sm">暂无匹配的情报数据</div>
                                ) : (
                                    <div className="flex flex-col">
                                        {results.map((msg, i) => (
                                            <motion.div
                                                key={i}
                                                initial={{ opacity: 0, y: 10 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: Math.min(i * 0.05, 0.5) }}
                                                className="group px-5 py-4 hover:bg-white/5 border-b border-white/5 transition-colors cursor-pointer flex gap-4"
                                            >
                                                <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0 border border-white/10 group-hover:bg-accent/10 transition-colors">
                                                    <span className="text-sm">💬</span>
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-[13px] text-white font-medium truncate">{msg.sender_name}</span>
                                                        <span className="text-[10px] text-accent4 bg-accent4/10 px-2 py-0.5 rounded-full whitespace-nowrap border border-accent4/20">{msg.group_title || 'Private'}</span>
                                                        <span className="text-[11px] text-text3 font-mono ml-auto">{msg.date}</span>
                                                    </div>
                                                    <div className="text-sm text-text2 leading-relaxed break-words">
                                                        {highlightNeon(msg.text, query)}
                                                    </div>
                                                </div>
                                                <div className="opacity-0 group-hover:opacity-100 flex items-center justify-center px-2 text-text3 transition-opacity">
                                                    <CornerDownLeft className="w-4 h-4" />
                                                </div>
                                            </motion.div>
                                        ))}
                                    </div>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>
        </div>
    );
}
