import { useState, useCallback } from 'react';
import './SetupControl.css';

interface ProgressEvent {
    event_type: 'start' | 'phase' | 'progress' | 'complete' | 'error';
    data_type?: 'regulations' | 'stewards_decisions' | 'race_data';
    phase?: 'discovery' | 'download' | 'index' | 'complete' | 'reset';
    current?: number;
    total?: number;
    item?: string;
    message?: string;
    totals?: { regulations: number; stewards_decisions: number; race_data: number };
}

interface DataTypeProgress {
    phase: string;
    current: number;
    total: number;
    item: string;
    message: string;
    status: 'waiting' | 'active' | 'complete' | 'error';
}

const PHASE_ICONS: Record<string, string> = {
    discovery: '🔍',
    download: '⏬',
    index: '💾',
    complete: '✅',
    reset: '🔄',
    waiting: '⏳',
    error: '❌',
};

const DATA_TYPE_CONFIG = {
    regulations: { label: 'Regulations', icon: '📚' },
    stewards_decisions: { label: 'Stewards Decisions', icon: '📋' },
    race_data: { label: 'Race Data', icon: '🏎️' },
};

export default function SetupControl() {
    const [isRunning, setIsRunning] = useState(false);
    const [season, setSeason] = useState(2025);
    const [reset, setReset] = useState(false);
    const [limit, setLimit] = useState(0);
    const [finalMessage, setFinalMessage] = useState('');
    const [error, setError] = useState('');


    const [progress, setProgress] = useState<Record<string, DataTypeProgress>>({
        regulations: { phase: '', current: 0, total: 0, item: '', message: '', status: 'waiting' },
        stewards_decisions: { phase: '', current: 0, total: 0, item: '', message: '', status: 'waiting' },
        race_data: { phase: '', current: 0, total: 0, item: '', message: '', status: 'waiting' },
    });

    const handleEvent = useCallback((event: ProgressEvent) => {
        if (event.event_type === 'start') {
            setFinalMessage('');
            setError('');
        } else if (event.event_type === 'phase' || event.event_type === 'progress') {
            if (event.data_type) {
                setProgress(prev => ({
                    ...prev,
                    [event.data_type!]: {
                        phase: event.phase || prev[event.data_type!].phase,
                        current: event.current ?? prev[event.data_type!].current,
                        total: event.total ?? prev[event.data_type!].total,
                        item: event.item || prev[event.data_type!].item,
                        message: event.message || '',
                        status: event.phase === 'complete' ? 'complete' : 'active',
                    },
                }));
            }
        } else if (event.event_type === 'complete') {
            setIsRunning(false);
            setFinalMessage(event.message || 'Setup complete!');
            if (event.totals) {
                setProgress(prev => ({
                    regulations: { ...prev.regulations, status: 'complete', message: `${event.totals!.regulations} docs` },
                    stewards_decisions: { ...prev.stewards_decisions, status: 'complete', message: `${event.totals!.stewards_decisions} docs` },
                    race_data: { ...prev.race_data, status: 'complete', message: `${event.totals!.race_data} docs` },
                }));
            }
        } else if (event.event_type === 'error') {
            if (event.data_type) {
                setProgress(prev => ({
                    ...prev,
                    [event.data_type!]: { ...prev[event.data_type!], status: 'error', message: event.message || 'Error' },
                }));
            }
            setError(event.message || 'Unknown error');
        }
    }, []);

    const startSetup = () => {
        setIsRunning(true);
        setFinalMessage('');
        setError('');
        setProgress({
            regulations: { phase: '', current: 0, total: 0, item: '', message: '', status: 'waiting' },
            stewards_decisions: { phase: '', current: 0, total: 0, item: '', message: '', status: 'waiting' },
            race_data: { phase: '', current: 0, total: 0, item: '', message: '', status: 'waiting' },
        });

        // Use fetch with POST for SSE (EventSource only supports GET)
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

        // Connect to SSE endpoint
        fetch(`${apiUrl}/api/v1/admin/setup/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ season, reset, limit }),
        })
            .then(async response => {
                const reader = response.body?.getReader();
                if (!reader) {
                    throw new Error('No response body');
                }

                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                handleEvent(data);
                            } catch (e) {
                                console.error('Failed to parse SSE event:', e);
                            }
                        }
                    }
                }

                setIsRunning(false);
            })
            .catch(err => {
                setError(err.message);
                setIsRunning(false);
            });
    };

    const cancelSetup = () => {
        // SSE cannot be cancelled from client side easily without AbortController
        // Just stop listening and reset UI
        setIsRunning(false);
        setError('Display stopped (process may continue on server)');
    };

    const renderProgressCard = (dataType: keyof typeof DATA_TYPE_CONFIG) => {
        const config = DATA_TYPE_CONFIG[dataType];
        const p = progress[dataType];
        const phaseIcon = p.phase ? PHASE_ICONS[p.phase] || PHASE_ICONS.waiting : PHASE_ICONS.waiting;
        const statusClass = p.status;
        const percentage = p.total > 0 ? Math.round((p.current / p.total) * 100) : 0;

        return (
            <div key={dataType} className={`progress-card ${statusClass}`}>
                <div className="progress-header">
                    <span className="data-icon">{config.icon}</span>
                    <span className="data-label">{config.label}</span>
                    <span className="phase-icon">{phaseIcon}</span>
                </div>

                {p.status === 'active' && p.total > 0 && (
                    <div className="progress-bar-container">
                        <div className="progress-bar" style={{ width: `${percentage}%` }} />
                        <span className="progress-text">{p.current}/{p.total}</span>
                    </div>
                )}

                {p.item && (
                    <div className="progress-item">{p.item.slice(0, 50)}</div>
                )}

                {p.message && (
                    <div className="progress-message">{p.message}</div>
                )}

                {p.status === 'waiting' && (
                    <div className="progress-waiting">Waiting...</div>
                )}
            </div>
        );
    };

    return (
        <div className="admin-page">
            <h1>🔧 Admin - Data Setup</h1>

            <div className="setup-controls">
                <div className="control-group">
                    <label>Season:</label>
                    <select value={season} onChange={e => setSeason(Number(e.target.value))} disabled={isRunning}>
                        <option value={2025}>2025</option>
                        <option value={2024}>2024</option>
                        <option value={2023}>2023</option>
                    </select>
                </div>

                <div className="control-group">
                    <label>
                        <input type="checkbox" checked={reset} onChange={e => setReset(e.target.checked)} disabled={isRunning} />
                        Reset data before indexing
                    </label>
                </div>

                <div className="control-group">
                    <label>Limit (0 = all):</label>
                    <input
                        type="number"
                        value={limit}
                        onChange={e => setLimit(Number(e.target.value))}
                        min={0}
                        disabled={isRunning}
                        style={{ width: '80px' }}
                    />
                </div>

                <div className="button-group">
                    {!isRunning ? (
                        <button className="btn btn-primary" onClick={startSetup}>
                            🔄 Run Setup
                        </button>
                    ) : (
                        <button className="btn btn-danger" onClick={cancelSetup}>
                            ⏹️ Cancel
                        </button>
                    )}
                </div>
            </div>

            <div className="progress-cards">
                {renderProgressCard('regulations')}
                {renderProgressCard('stewards_decisions')}
                {renderProgressCard('race_data')}
            </div>

            {finalMessage && (
                <div className="final-message success">
                    ✅ {finalMessage}
                </div>
            )}

            {error && (
                <div className="final-message error">
                    ❌ {error}
                </div>
            )}
        </div>
    );
}
