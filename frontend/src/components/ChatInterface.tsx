import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api, type SourceInfo } from '../services/api';

interface Message {
    role: 'user' | 'agent';
    content: string;
    sources?: SourceInfo[];
    isLoading?: boolean;
}

export const ChatInterface: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [query, setQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim() || isLoading) return;

        const userMessage: Message = { role: 'user', content: query };
        const tempAgentMessage: Message = { role: 'agent', content: '', isLoading: true };

        setMessages(prev => [...prev, userMessage, tempAgentMessage]);
        setQuery('');
        setIsLoading(true);

        try {
            // Prepare history (exclude the current user message being added and temp loading message)
            // Limit to last 6 messages to keep context focused
            const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));

            const data = await api.askQuestion(userMessage.content, history);
            setMessages(prev => {
                const newMessages = [...prev];
                // Replace temp loading message with actual response
                newMessages[newMessages.length - 1] = {
                    role: 'agent',
                    content: data.answer,
                    sources: data.sources
                };
                return newMessages;
            });
        } catch (err: any) {
            setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                    role: 'agent',
                    content: `Error: ${err.message || "Failed to retrieve answer."}`
                };
                return newMessages;
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full max-w-4xl mx-auto backdrop-blur-md bg-white/10 border border-white/20 rounded-xl overflow-hidden shadow-2xl">
            {/* Header Ribbon */}
            <div className="bg-f1-red px-4 py-2 flex items-center justify-between shadow-lg z-10">
                <span className="text-xs font-black uppercase tracking-widest text-white italic">
                    PitWall Live Feed // Session Active
                </span>
                <div className="flex space-x-1">
                    <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
                </div>
            </div>

            {/* Chat History Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-f1-red scrollbar-track-transparent">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-f1-silver/50 space-y-4">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                        <p className="text-sm font-medium italic text-white/50">Awaiting telemetry... Ask about penalties or regulations.</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}>
                        {/* F1 Radio Message Card */}
                        <div className={`max-w-[95%] md:max-w-[85%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                            {/* Radio Header Bar - F1 Broadcast Style */}
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-t-lg ${msg.role === 'user'
                                ? 'bg-gradient-to-r from-f1-red to-red-700'
                                : 'bg-gradient-to-r from-slate-200 to-slate-300'
                                }`}>
                                {/* Live Indicator */}
                                <div className="flex items-center gap-1.5">
                                    <div className={`w-2 h-2 rounded-full ${msg.role === 'user' ? 'bg-white' : 'bg-f1-red'
                                        } ${msg.isLoading ? 'animate-pulse' : ''} shadow-lg`}></div>
                                    <span className={`text-[10px] font-black uppercase tracking-[0.15em] ${msg.role === 'user' ? 'text-white' : 'text-slate-800'}`}>
                                        {msg.role === 'user' ? 'DRIVER' : 'RACE ENGINEER'}
                                    </span>
                                </div>

                                {/* Separator */}
                                <div className="flex-1 h-px bg-white/20"></div>

                                {/* Timestamp Badge */}
                                <span className={`text-[9px] font-mono px-2 py-0.5 rounded ${msg.role === 'user' ? 'text-white/70 bg-black/30' : 'text-slate-600 bg-slate-400/30'}`}>
                                    {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                                </span>
                            </div>

                            {/* Message Content Area */}
                            <div className={`relative px-4 py-3 rounded-b-lg shadow-lg ${msg.role === 'user'
                                ? 'bg-gradient-to-br from-f1-red/90 to-red-800/90 text-white border-l-4 border-white/50'
                                : 'bg-gradient-to-br from-white/95 to-slate-100/95 text-slate-900 border-l-4 border-f1-red backdrop-blur-sm'
                                }`}>
                                {/* Subtle scan line effect for agent messages */}
                                {msg.role === 'agent' && !msg.isLoading && (
                                    <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-5">
                                        <div className="absolute inset-0 bg-[linear-gradient(transparent_50%,rgba(255,255,255,0.05)_50%)] bg-[length:100%_4px]"></div>
                                    </div>
                                )}

                                {msg.isLoading ? (
                                    <div className="flex items-center gap-3 py-2">
                                        <div className="flex space-x-1">
                                            <div className="w-2 h-2 bg-f1-red rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                            <div className="w-2 h-2 bg-white rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                            <div className="w-2 h-2 bg-f1-red rounded-full animate-bounce"></div>
                                        </div>
                                        <span className="text-xs text-slate-500 font-medium italic">Analyzing telemetry...</span>
                                    </div>
                                ) : (
                                    <div className={`prose prose-sm max-w-none leading-relaxed
                                        ${msg.role === 'user'
                                            ? 'prose-invert prose-p:text-white/95 prose-headings:text-white prose-strong:text-white prose-li:border-white/50'
                                            : 'prose-slate prose-p:text-slate-800 prose-headings:text-slate-900 prose-strong:text-slate-900 prose-li:border-f1-red'
                                        }
                                        prose-p:mb-2 prose-p:text-sm
                                        prose-headings:font-black prose-headings:uppercase prose-headings:tracking-tight prose-headings:text-base
                                        prose-a:text-f1-red prose-a:no-underline hover:prose-a:underline
                                        prose-ul:list-none prose-ul:pl-0 prose-li:pl-4 prose-li:border-l-2 prose-li:mb-1
                                        prose-code:bg-black/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-f1-red prose-code:text-xs`}>
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                )}
                            </div>

                            {/* Sources Section - Styled as Data Feed */}
                            {msg.sources && msg.sources.length > 0 && (() => {
                                const displayableSources = msg.sources.filter(s =>
                                    s.doc_type !== 'race_control' &&
                                    s.doc_type !== 'race_data'
                                );

                                if (displayableSources.length === 0) return null;

                                return (
                                    <div className="bg-black/80 px-3 py-2 border-t border-f1-grey/20">
                                        <div className="flex items-center gap-2 mb-2">
                                            <div className="w-1 h-1 bg-cyan-400 rounded-full"></div>
                                            <span className="text-[8px] font-black uppercase tracking-[0.2em] text-cyan-400">DATA SOURCES</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1.5">
                                            {displayableSources.map((source, sIdx) => {
                                                const Content = (
                                                    <span className="flex items-center gap-1">
                                                        <span className="truncate max-w-[120px] text-[9px] font-mono">{source.title}</span>
                                                        {source.url && <span className="text-cyan-400 text-[8px]">↗</span>}
                                                    </span>
                                                );

                                                if (source.url) {
                                                    return (
                                                        <a
                                                            key={sIdx}
                                                            href={source.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="flex items-center bg-slate-800/80 hover:bg-f1-red border border-slate-700 hover:border-f1-red text-white/70 hover:text-white px-2 py-1 rounded transition-all duration-200"
                                                            title={source.excerpt || ""}
                                                        >
                                                            {Content}
                                                        </a>
                                                    );
                                                }
                                                return (
                                                    <div
                                                        key={sIdx}
                                                        className="flex items-center bg-slate-800/50 border border-slate-700/50 text-white/50 px-2 py-1 rounded"
                                                        title={source.excerpt || ""}
                                                    >
                                                        {Content}
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })()}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSubmit} className="p-4 bg-black/40 border-t border-f1-grey/20">
                <div className="relative flex items-center">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Type your question..."
                        disabled={isLoading}
                        className="w-full bg-f1-black border border-f1-grey/50 focus:border-f1-red rounded-full px-5 py-3 text-white placeholder-gray-400 transition-all font-medium focus:outline-none focus:ring-2 focus:ring-f1-red/50 focus:bg-f1-black shadow-inner"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !query.trim()}
                        className="absolute right-2 p-2 bg-f1-red text-white rounded-full hover:bg-red-600 disabled:opacity-50 disabled:hover:bg-f1-red transition-colors shadow-lg"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                        </svg>
                    </button>
                </div>
            </form>
        </div>
    );
};
