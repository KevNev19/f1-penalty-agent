import React, { useState } from 'react';

interface ResponseData {
    answer: string;
    sources_used: string[];
}

const PenaltyAgent: React.FC = () => {
    const [query, setQuery] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [response, setResponse] = useState<ResponseData | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setIsLoading(true);
        setError(null);
        setResponse(null);

        try {
            const res = await fetch('http://localhost:8000/api/v1/ask', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: query }),
            });

            if (!res.ok) {
                throw new Error('Failed to connect to PitWallAI engine.');
            }

            const data = await res.json();
            setResponse(data);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="w-full max-w-4xl mx-auto mt-12">
            <div className="bg-f1-grey/10 border border-f1-grey/20 rounded-sm overflow-hidden backdrop-blur-md">
                {/* Header Ribbon */}
                <div className="bg-f1-red px-4 py-1 flex items-center justify-between">
                    <span className="text-[10px] font-black uppercase tracking-widest text-white italic">
                        PitWall Engine v1.0 // Data Stream active
                    </span>
                    <div className="flex space-x-1">
                        <div className="w-1 h-1 bg-white/40"></div>
                        <div className="w-1 h-1 bg-white/40"></div>
                        <div className="w-1 h-1 bg-white/40"></div>
                    </div>
                </div>

                {/* Query Input */}
                <form onSubmit={handleSubmit} className="p-6">
                    <div className="relative">
                        <input
                            type="text"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            placeholder="Query regulations (e.g., 'Track limits at Copse Corner')..."
                            className="w-full bg-black/40 border-b-2 border-f1-grey focus:border-f1-red outline-none px-4 py-3 text-white placeholder-f1-silver/50 transition-all font-medium italic"
                        />
                        <button
                            type="submit"
                            disabled={isLoading}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-f1-red hover:text-white transition-colors"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                            </svg>
                        </button>
                    </div>
                </form>

                {/* Results Area */}
                {(isLoading || response || error) && (
                    <div className="border-t border-f1-grey/20 p-6 bg-black/20">
                        {isLoading && (
                            <div className="space-y-4 animate-pulse">
                                <div className="h-4 bg-f1-grey/40 w-3/4"></div>
                                <div className="h-4 bg-f1-grey/40 w-1/2"></div>
                                <div className="h-20 bg-f1-grey/20 w-full rounded-sm"></div>
                            </div>
                        )}

                        {error && (
                            <div className="border-l-4 border-f1-red bg-f1-red/10 p-4">
                                <p className="text-sm font-bold text-f1-red">ENGINE ERROR</p>
                                <p className="text-white mt-1">{error}</p>
                            </div>
                        )}

                        {response && (
                            <div className="space-y-6">
                                <div>
                                    <div className="flex items-center space-x-2 mb-4">
                                        <span className="w-2 h-2 bg-f1-red rounded-full"></span>
                                        <span className="text-xs font-bold text-f1-red uppercase tracking-widest">Analysis Result</span>
                                    </div>
                                    <div className="prose prose-invert max-w-none text-f1-silver leading-relaxed">
                                        {response.answer}
                                    </div>
                                </div>

                                {response.sources_used && response.sources_used.length > 0 && (
                                    <div className="border-t border-f1-grey/10 pt-4">
                                        <p className="text-[10px] font-bold text-f1-silver uppercase tracking-widest mb-3">Supporting Documentation</p>
                                        <div className="flex flex-wrap gap-2">
                                            {response.sources_used.map((source, idx) => (
                                                <span key={idx} className="bg-f1-grey/30 px-3 py-1 rounded-sm text-[10px] text-f1-silver border border-f1-grey/40 uppercase tracking-tighter">
                                                    {source.split('/').pop()}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default PenaltyAgent;
