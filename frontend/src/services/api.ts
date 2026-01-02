export interface SourceInfo {
    title: string;
    doc_type: string;
    relevance_score: number;
    excerpt: string | null;
    url?: string;
}

export interface AnswerResponse {
    answer: string;
    sources: SourceInfo[];
    question: string;
    model_used: string;
}

export interface HealthResponse {
    status: string;
    version: string;
    vector_store: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiService {
    private baseUrl: string;

    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        // Remove trailing slash from baseUrl if present to avoid double slashes
        const cleanBaseUrl = this.baseUrl.replace(/\/$/, '');
        const url = `${cleanBaseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        const response = await fetch(url, { ...options, headers });

        if (!response.ok) {
            const errorBody = await response.text();
            throw new Error(`API Error: ${response.status} ${response.statusText} - ${errorBody}`);
        }

        return response.json();
    }

    async askQuestion(question: string, messages: { role: string, content: string }[] = []): Promise<AnswerResponse> {
        return this.request<AnswerResponse>('/api/v1/ask', {
            method: 'POST',
            body: JSON.stringify({ question, messages }),
        });
    }

    async checkHealth(): Promise<HealthResponse> {
        return this.request<HealthResponse>('/api/v1/health');
    }

    async checkReadiness(): Promise<HealthResponse> {
        return this.request<HealthResponse>('/api/v1/ready');
    }

    /**
     * Ask a question with streaming response using Server-Sent Events.
     * @param question - The question to ask
     * @param onChunk - Callback called for each text chunk received
     * @param onDone - Callback called when streaming is complete
     * @param onError - Callback called on error
     */
    async askQuestionStream(
        question: string,
        onChunk: (chunk: string) => void,
        onDone: () => void,
        onError: (error: string) => void
    ): Promise<void> {
        const cleanBaseUrl = this.baseUrl.replace(/\/$/, '');
        const url = `${cleanBaseUrl}/api/v1/ask/stream`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, messages: [] }),
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }

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
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.type === 'chunk') {
                                onChunk(parsed.content);
                            } else if (parsed.type === 'done') {
                                onDone();
                                return;
                            } else if (parsed.type === 'error') {
                                onError(parsed.message);
                                return;
                            }
                        } catch {
                            // Ignore parse errors for incomplete data
                        }
                    }
                }
            }
            onDone();
        } catch (err: any) {
            onError(err.message || 'Streaming failed');
        }
    }
}

export const api = new ApiService();
