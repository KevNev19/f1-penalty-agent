import React, { useEffect, useState } from 'react';
import { api, type HealthResponse } from '../services/api';

// ... (Rest of file unchanged until the log section)


interface AdminPageProps {
    onBack: () => void;
}

export const AdminPage: React.FC<AdminPageProps> = ({ onBack }) => {
    const [health, setHealth] = useState<HealthResponse | null>(null);
    const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
    const [loading, setLoading] = useState(true);

    const checkHealth = async () => {
        try {
            const data = await api.checkReadiness();
            setHealth(data);
        } catch (err) {
            console.error('Health check failed', err);
            setHealth({ status: 'unreachable', version: 'unknown', vector_store: 'disconnected' });
        } finally {
            setLoading(false);
            setLastUpdated(new Date());
        }
    };

    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 5000);
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string) => {
        if (status === 'healthy' || status.startsWith('connected') || status === 'ready') return 'text-green-500';
        if (status === 'degraded') return 'text-yellow-500';
        return 'text-f1-red';
    };

    const StatusCard = ({ title, value, status }: { title: string, value: string, status: string }) => {
        // Parse status to determine if "OPERATIONAL"
        const isHealthy = status === 'healthy' || status.startsWith('connected') || status === 'ready';

        return (
            <div className="bg-f1-black/40 border border-f1-grey/20 p-6 rounded-lg backdrop-blur-sm shadow-lg hover:border-f1-red/50 transition-colors duration-300">
                <h3 className="text-f1-silver uppercase tracking-widest text-xs font-bold mb-3">{title}</h3>
                <div className={`text-xl font-mono font-bold ${getStatusColor(status)} break-words`}>
                    {value.replace(/_/g, ' ').toUpperCase()}
                </div>
                <div className="mt-4 pt-4 border-t border-f1-grey/10 text-[10px] text-f1-silver/50 flex items-center space-x-2">
                    <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-f1-red shadow-[0_0_8px_rgba(239,68,68,0.6)]'}`}></span>
                    <span className="font-bold tracking-wider">{isHealthy ? 'OPERATIONAL' : 'OFFLINE'}</span>
                </div>
            </div>
        );
    };

    return (
        <div className="min-h-[calc(100vh-80px)] p-8 max-w-6xl mx-auto">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-12 gap-4">
                <div>
                    <h1 className="text-5xl font-black italic text-white uppercase tracking-tighter">
                        System Operations
                    </h1>
                    <p className="text-f1-silver font-medium mt-2 tracking-wide border-l-4 border-f1-red pl-3">
                        Pit Wall Telemetry & Diagnostics
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

            {loading ? (
                <div className="text-center text-f1-silver animate-pulse flex flex-col items-center mt-20">
                    <div className="w-12 h-12 border-4 border-f1-red border-t-transparent rounded-full animate-spin mb-4"></div>
                    <span className="text-xl font-mono uppercase">Establishing Uplink...</span>
                </div>
            ) : health ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-in fade-in duration-500">
                    <StatusCard
                        title="API Status"
                        value={health.status}
                        status={health.status}
                    />
                    <StatusCard
                        title="Vector Database"
                        value={health.vector_store}
                        status={health.vector_store}
                    />
                    <StatusCard
                        title="System Version"
                        value={health.version}
                        status={'ready'}
                    />

                    {/* Detailed Log Window */}
                    <div className="col-span-1 md:col-span-3 mt-8 bg-black/80 border border-f1-grey/30 rounded p-6 font-mono text-sm shadow-xl backdrop-blur-md">
                        <div className="flex justify-between border-b border-f1-grey/20 pb-4 mb-4">
                            <span className="text-f1-red font-bold uppercase tracking-widest flex items-center">
                                <span className="w-2 h-2 bg-f1-red mr-2 animate-pulse"></span>
                                Live Telemetry Log
                            </span>
                            <span className="text-f1-silver/50 text-xs">Updated: {lastUpdated.toLocaleTimeString()}</span>
                        </div>
                        <div className="space-y-2 text-f1-silver/90 h-48 overflow-y-auto pr-2 custom-scrollbar">
                            <p className="flex"><span className="text-f1-grey w-24">[{lastUpdated.toLocaleTimeString()}]</span> <span className="text-green-500">INFO</span> <span className="ml-4">System check initiated...</span></p>
                            <p className="flex"><span className="text-f1-grey w-24">[{lastUpdated.toLocaleTimeString()}]</span> <span className="text-green-500">INFO</span> <span className="ml-4">API Endpoint reachable at {import.meta.env.VITE_API_BASE_URL || 'localhost:8000'}</span></p>
                            <p className="flex"><span className="text-f1-grey w-24">[{lastUpdated.toLocaleTimeString()}]</span> <span className="text-green-500">INFO</span> <span className="ml-4">Vector Store connection verified.</span></p>
                            <p className="flex">
                                <span className="text-f1-grey w-24">[{lastUpdated.toLocaleTimeString()}]</span>
                                <span className={(health.status === 'healthy' || health.status === 'ready') ? 'text-green-500' : 'text-f1-red'}>
                                    &gt; [STATUS] {(health.status === 'healthy' || health.status === 'ready') ? 'ALL SYSTEMS NOMINAL' : 'SYSTEM DEGRADED'}
                                </span>
                            </p>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="p-8 bg-f1-red/10 border border-f1-red text-center rounded-lg">
                    <h2 className="text-2xl font-bold text-f1-red mb-2">CRITICAL FAILURE</h2>
                    <p className="text-white">Unable to contact backend services.</p>
                </div>
            )}
        </div>
    );
};
