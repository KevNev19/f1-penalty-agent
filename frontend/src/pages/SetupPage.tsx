import React from 'react';
import SetupControl from '../components/SetupControl';

interface SetupPageProps {
    onBack: () => void;
}

export const SetupPage: React.FC<SetupPageProps> = ({ onBack }) => {
    return (
        <div className="min-h-[calc(100vh-80px)] p-8 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-12 gap-4">
                <div>
                    <h1 className="text-5xl font-black italic text-white uppercase tracking-tighter">
                        Setup
                    </h1>
                    <p className="text-f1-silver font-medium mt-2 tracking-wide border-l-4 border-f1-red pl-3">
                        Data Ingestion & Indexing
                    </p>
                </div>
                <button
                    onClick={onBack}
                    className="flex items-center justify-center space-x-2 px-8 py-4 bg-f1-red hover:bg-red-600 text-white font-bold rounded uppercase tracking-wider transition-all hover:scale-105 shadow-[0_0_15px_rgba(239,68,68,0.4)]"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
                    </svg>
                    <span>Back to Pit Wall</span>
                </button>
            </div>

            {/* Setup Control Panel */}
            <div className="mt-8">
                <SetupControl />
            </div>
        </div>
    );
};
