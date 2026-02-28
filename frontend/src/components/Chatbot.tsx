import { useState, useRef, useEffect } from 'react';

type Citation = {
    id: number;
    group_id: number;
    sender_name: string;
    date: string;
    text: string;
};

type ChatMessage = {
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
    isError?: boolean;
    isLoading?: boolean;
};

export function Chatbot() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputValue, setInputValue] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const endOfMessagesRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!inputValue.trim() || isTyping) return;

        const query = inputValue.trim();
        setInputValue('');
        setMessages(prev => [...prev, { role: 'user', content: query }]);
        setMessages(prev => [...prev, { role: 'assistant', content: '', isLoading: true }]);
        setIsTyping(true);

        try {
            const res = await fetch('/api/chat/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();

            setMessages(prev => {
                const newArr = [...prev];
                newArr[newArr.length - 1] = {
                    role: 'assistant',
                    content: data.answer || "接口未返回文字",
                    citations: data.citations || [],
                    isLoading: false
                };
                return newArr;
            });
        } catch (error) {
            setMessages(prev => {
                const newArr = [...prev];
                newArr[newArr.length - 1] = {
                    role: 'assistant',
                    content: "网络异常或请求超时，无法连接至 AI 代理。",
                    isError: true,
                    isLoading: false
                };
                return newArr;
            });
        } finally {
            setIsTyping(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-140px)] glass-panel rounded-2xl relative z-10 overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border-subtle flex justify-between items-center bg-black/40 backdrop-blur-md relative z-20">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-accent5/20 flex items-center justify-center text-accent5">
                        🤖
                    </div>
                    <div>
                        <h3 className="text-[16px] font-bold text-white tracking-wide">
                            RAG 私人智库
                        </h3>
                        <p className="text-[11px] text-text3 font-medium">
                            基于您个人监控群组的垂直视角 AI 问答引擎
                        </p>
                    </div>
                </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-black/10">
                {messages.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center text-center opacity-70">
                        <div className="w-20 h-20 bg-accent5/10 rounded-full flex items-center justify-center mb-4 text-4xl shadow-[0_0_30px_rgba(139,92,246,0.2)] border border-accent5/20">
                            🤖
                        </div>
                        <h3 className="text-xl font-bold text-white mb-2">我是您的私有知识管家</h3>
                        <p className="text-sm text-text3 max-w-sm leading-relaxed">
                            我已经学习了所有的历史聊天记录。您可以随时向我提问特定话题的走向、相关结论或者用户评价，我会为您检索和整理。
                        </p>
                        <div className="flex gap-3 mt-8">
                            <span
                                onClick={() => setInputValue("最近关于 ChatGPT 的讨论有什么重要的？")}
                                className="px-3 py-1.5 bg-white/5 rounded-[6px] text-xs font-mono text-text2 cursor-pointer hover:bg-white/10 hover:text-white transition-colors"
                            >
                                最近关于 ChatGPT 的讨论有什么重要的？
                            </span>
                        </div>
                    </div>
                )}

                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`flex gap-3 max-w-[85%] lg:max-w-[75%] ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                            <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-sm font-bold mt-1 shadow-lg"
                                style={{ backgroundColor: msg.role === 'user' ? 'var(--color-accent)' : 'var(--color-accent5)' }}>
                                {msg.role === 'user' ? 'U' : 'AI'}
                            </div>

                            <div className="flex flex-col gap-1.5 min-w-0">
                                <div className={`text-[12px] text-text3 font-medium px-1 flex items-center gap-2 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                                    {msg.role === 'user' ? 'You' : 'TG Monitor RAG'}
                                    {msg.role === 'assistant' && msg.isLoading && (
                                        <span className="flex items-center gap-1">
                                            <span className="w-1.5 h-1.5 bg-accent5 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                            <span className="w-1.5 h-1.5 bg-accent5 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                            <span className="w-1.5 h-1.5 bg-accent5 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                        </span>
                                    )}
                                </div>

                                <div className={`px-5 py-3.5 text-sm leading-relaxed whitespace-pre-wrap break-words rounded-2xl shadow-sm ${msg.role === 'user'
                                        ? 'bg-accent/20 border border-accent/30 text-white rounded-tr-sm'
                                        : msg.isError
                                            ? 'bg-red-500/10 border border-red-500/30 text-red-200 rounded-tl-sm'
                                            : 'bg-white/5 border border-white/10 text-text-main rounded-tl-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] pt-4 relative'
                                    }`}>
                                    {msg.isLoading ? (
                                        <div className="text-text3 italic animate-pulse">正在向量库中检索您的碎片记忆片段...</div>
                                    ) : (
                                        <>
                                            {/* We use a simple regex replacing [1] tags with styled spans */}
                                            {msg.content.split(/(\[\d+\])/g).map((part, idx) => {
                                                if (/^\[\d+\]$/.test(part)) {
                                                    return <span key={idx} className="inline-flex text-[10px] items-center justify-center bg-accent5/30 text-accent5 border border-accent5/50 px-1 py-0 min-w-[1.2rem] h-[1.2rem] rounded-full mx-0.5 align-text-top font-bold cursor-pointer hover:bg-accent5 hover:text-white transition-colors">
                                                        {part.slice(1, -1)}
                                                    </span>;
                                                }
                                                return <span key={idx}>{part}</span>;
                                            })}
                                        </>
                                    )}
                                </div>

                                {/* Citations block rendered directly below message */}
                                {msg.citations && msg.citations.length > 0 && (
                                    <div className="mt-2 text-xs">
                                        <details className="group border border-white/5 bg-black/20 rounded-xl overflow-hidden [&_summary::-webkit-details-marker]:hidden">
                                            <summary className="flex items-center justify-between px-4 py-2 cursor-pointer font-medium text-text3 hover:text-accent5 hover:bg-white/5 transition-colors user-select-none">
                                                <span className="flex items-center gap-2">
                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                                                    展开知识引用根源 ({msg.citations.length} 条)
                                                </span>
                                                <span className="transition group-open:rotate-180">
                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                                                </span>
                                            </summary>
                                            <div className="p-4 border-t border-white/5 bg-black/40 space-y-3 custom-scrollbar max-h-[300px] overflow-y-auto">
                                                {msg.citations.map(c => (
                                                    <div key={c.id} className="text-[12px] bg-white/5 rounded-lg p-3 border border-white/5 shadow-inner">
                                                        <div className="flex gap-2 items-center text-[10px] text-text3 mb-1.5 font-mono">
                                                            <span className="bg-accent5/30 text-accent5 px-1.5 py-[1px] rounded font-bold border border-accent5/40">[{c.id}]</span>
                                                            <span className="truncate max-w-[120px] font-bold text-accent5/70">{c.sender_name}</span>
                                                            <span>•</span>
                                                            <span>{c.date.slice(0, 16).replace('T', ' ')}</span>
                                                        </div>
                                                        <div className="text-text2 leading-relaxed break-words pl-1">{c.text}</div>
                                                    </div>
                                                ))}
                                            </div>
                                        </details>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
                <div ref={endOfMessagesRef} />
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-border-subtle bg-black/30 backdrop-blur-md relative z-20">
                <div className="relative flex items-center shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_4px_20px_rgba(0,0,0,0.5)] bg-white/5 rounded-2xl pr-2 overflow-hidden border border-white/10 focus-within:border-accent5/50 focus-within:ring-1 focus-within:ring-accent5/50 transition-all">
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="想查询任何群聊里错过的细节？"
                        className="w-full bg-transparent border-none text-sm text-text-main py-4 pl-5 focus:outline-none focus:ring-0 resize-none h-14 custom-scrollbar"
                        disabled={isTyping}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isTyping}
                        className="ml-2 w-10 h-10 shrink-0 flex items-center justify-center rounded-xl bg-accent5/20 text-accent5 hover:bg-accent5 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <svg className="w-5 h-5 -ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                        </svg>
                    </button>
                </div>
                <div className="text-center mt-3 text-[10px] font-mono text-text3">
                    Shift + Enter 以换行, Enter 发送 | RAG 检索模型可能会产生幻觉，请通过引用框进行核实。
                </div>
            </div>
        </div>
    );
}
