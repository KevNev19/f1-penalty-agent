import React, { useState, useRef, useEffect } from 'react';
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
        <div className="flex flex-col h-[calc(100vh-140px)] max-w-4xl mx-auto backdrop-blur-sm bg-black/20 border border-f1-grey/20 rounded-lg overflow-hidden mt-4 shadow-2xl">
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
                        <p className="text-sm font-medium italic">Awaiting telemetry... Ask about penalties or regulations.</p>
                    </div>
                )}

                {messages.map((msg, idx) => (
                    <div key={idx} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <div
                            className={`max-w-[85%] rounded-lg p-4 shadow-md ${msg.role === 'user'
                                ? 'bg-f1-red text-white rounded-br-none'
                                : 'bg-f1-black/80 border border-f1-grey/30 text-f1-silver rounded-bl-none'
                                }`}
                        >
                            {msg.role === 'agent' && (
                                <div className="flex items-center space-x-2 mb-2 border-b border-f1-grey/20 pb-2">
                                    <span className="w-1.5 h-1.5 bg-f1-red rounded-full"></span>
                                    <span className="text-[10px] font-bold uppercase tracking-widest text-f1-red">Race Control</span>
                                </div>
                            )}

                            {msg.isLoading ? (
                                <div className="flex space-x-2 h-6 items-center px-2">
                                    <div className="w-2 h-2 bg-f1-silver/50 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                    <div className="w-2 h-2 bg-f1-silver/50 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                    <div className="w-2 h-2 bg-f1-silver/50 rounded-full animate-bounce"></div>
                                </div>
                            ) : (
                                <div className="prose prose-invert prose-sm max-w-none whitespace-pre-line leading-relaxed">
                                    {msg.content}
                                </div>
                            )}

                            {/* Sources Section - Filtered */}
                            {msg.sources && msg.sources.length > 0 && (() => {
                                // FILTER LOGIC: Exclude race data citations from visual display
                                const displayableSources = msg.sources.filter(s =>
                                    s.doc_type !== 'race_control' &&
                                    s.doc_type !== 'race_data'
                                );

                                if (displayableSources.length === 0) return null;

                                return (
                                    <div className="mt-4 pt-3 border-t border-f1-grey/20">
                                        <p className="text-[10px] font-bold text-f1-silver/60 uppercase tracking-widest mb-2">References</p>
                                        <div className="flex flex-wrap gap-2">
                                            {displayableSources.map((source, sIdx) => {
                                                const Content = (
                                                    <span className="flex items-center space-x-1">
                                                        <span className="truncate max-w-[150px]">{source.title}</span>
                                                        {source.url && <span className="text-[10px] opacity-70">↗</span>}
                                                    </span>
                                                );

                                                if (source.url) {
                                                    return (
                                                        <a
                                                            key={sIdx}
                                                            href={source.url}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="flex items-center text-[10px] bg-f1-grey/20 hover:bg-f1-red/20 border border-f1-grey/30 hover:border-f1-red/50 text-f1-silver hover:text-white px-2 py-1 rounded transition-colors"
                                                            title={source.excerpt || ""}
                                                        >
                                                            {Content}
                                                        </a>
                                                    );
                                                }
                                                return (
                                                    <div
                                                        key={sIdx}
                                                        className="flex items-center text-[10px] bg-f1-grey/10 border border-f1-grey/20 text-f1-silver/70 px-2 py-1 rounded cursor-help"
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
                        className="w-full bg-f1-black/50 border border-f1-grey/30 focus:border-f1-red rounded-full px-5 py-3 text-white placeholder-f1-silver/30 transition-all font-medium focus:outline-none focus:ring-1 focus:ring-f1-red/50 focus:bg-f1-black/80"
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
