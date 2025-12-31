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
        return this.request<HealthResponse>('/health');
    }

    async checkReadiness(): Promise<HealthResponse> {
        return this.request<HealthResponse>('/ready');
    }
}

export const api = new ApiService();
