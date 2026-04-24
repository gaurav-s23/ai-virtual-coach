import axios from 'axios';

// In local dev, fallback to backend container port if env is missing.
const DEFAULT_API_URL = "http://localhost:8000";

// Validate and construct API base URL
const getValidApiUrl = () => {
    const envUrl = import.meta?.env?.VITE_API_URL?.trim();
    const apiUrl = envUrl || DEFAULT_API_URL;
    
    // Basic URL validation
    try {
        const url = new URL(apiUrl);
        // Only allow http/https protocols
        if (!['http:', 'https:'].includes(url.protocol)) {
            console.warn('Invalid API URL protocol, falling back to default');
            return DEFAULT_API_URL;
        }
        // Remove trailing slash
        return apiUrl.replace(/\/$/, '');
    } catch (error) {
        console.warn('Invalid API URL format, falling back to default:', error);
        return DEFAULT_API_URL;
    }
};

export const API_BASE = getValidApiUrl();

// General API for quick operations (auth, user data, etc.)
const api = axios.create({
    baseURL: API_BASE,
    timeout: 8000, // 8 second timeout for general endpoints
});

// Create specialized API instances for different timeout requirements
const longRunningApi = axios.create({
    baseURL: API_BASE,
    timeout: 120000, // 120 second timeout for LLM/RAG heavy operations
});

// Medium timeout API for standard operations
const mediumApi = axios.create({
    baseURL: API_BASE,
    timeout: 30000, // 30 second timeout for standard operations
});

// Add request interceptor for long-running API
longRunningApi.interceptors.request.use(async (config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Add response interceptor for long-running API
longRunningApi.interceptors.response.use(
    (response) => response,
    async (error) => {
        const config = error.config || {};
        const status = error?.response?.status;
        config.__retryCount = config.__retryCount || 0;
        
        // Retry on network errors and server errors (not auth errors)
        const shouldRetry = (
            // Network errors (no response)
            !error.response ||
            // Server errors
            status === 503 || // Service Unavailable
            status === 502 || // Bad Gateway
            status === 500 || // Internal Server Error
            status === 504    // Gateway Timeout
        ) && config.__retryCount < 3;
        
        if (shouldRetry) {
            config.__retryCount += 1;
            // Exponential backoff with jitter
            const baseDelay = 1000;
            const maxDelay = 10000;
            const exponentialDelay = Math.min(baseDelay * Math.pow(2, config.__retryCount - 1), maxDelay);
            const jitter = Math.random() * 0.3 * exponentialDelay;
            const delay = exponentialDelay + jitter;
            
            console.warn(`Retrying long-running request (attempt ${config.__retryCount}/3) after ${Math.round(delay)}ms delay`);
            await new Promise((resolve) => setTimeout(resolve, delay));
            return longRunningApi(config);
        }
        return Promise.reject(error);
    }
);

// Add request and response interceptors to mediumApi
mediumApi.interceptors.request.use(async (config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

mediumApi.interceptors.response.use(
    (response) => response,
    async (error) => {
        const config = error.config || {};
        const status = error?.response?.status;
        config.__retryCount = config.__retryCount || 0;
        
        // Retry on network errors and server errors (not auth errors)
        const shouldRetry = (
            // Network errors (no response)
            !error.response ||
            // Server errors
            status === 503 || // Service Unavailable
            status === 502 || // Bad Gateway
            status === 500 || // Internal Server Error
            status === 504    // Gateway Timeout
        ) && config.__retryCount < 3;
        
        if (shouldRetry) {
            config.__retryCount += 1;
            // Exponential backoff with jitter
            const baseDelay = 1000;
            const maxDelay = 10000;
            const exponentialDelay = Math.min(baseDelay * Math.pow(2, config.__retryCount - 1), maxDelay);
            const jitter = Math.random() * 0.3 * exponentialDelay;
            const delay = exponentialDelay + jitter;
            
            console.warn(`Retrying medium request (attempt ${config.__retryCount}/3) after ${Math.round(delay)}ms delay`);
            await new Promise((resolve) => setTimeout(resolve, delay));
            return mediumApi(config);
        }
        return Promise.reject(error);
    }
);

// Add connectivity check
api.interceptors.request.use(async (config) => {
    const token = localStorage.getItem("token");
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const config = error.config || {};
        const status = error?.response?.status;
        config.__retryCount = config.__retryCount || 0;
        
        // Retry on network errors and server errors (not auth errors)
        const shouldRetry = (
            // Network errors (no response)
            !error.response ||
            // Server errors
            status === 503 || // Service Unavailable
            status === 502 || // Bad Gateway
            status === 500 || // Internal Server Error
            status === 504    // Gateway Timeout
        ) && config.__retryCount < 3;
        
        if (shouldRetry) {
            config.__retryCount += 1;
            // Exponential backoff with jitter
            const baseDelay = 1000;
            const maxDelay = 10000;
            const exponentialDelay = Math.min(baseDelay * Math.pow(2, config.__retryCount - 1), maxDelay);
            const jitter = Math.random() * 0.3 * exponentialDelay;
            const delay = exponentialDelay + jitter;
            
            console.warn(`Retrying request (attempt ${config.__retryCount}/3) after ${Math.round(delay)}ms delay`);
            await new Promise((resolve) => setTimeout(resolve, delay));
            return api(config);
        }
        return Promise.reject(error);
    }
);

// Login Function
export const loginUser = async (credentials) => {
    try {
        const response = await api.post('/api/login', credentials);
        const tok = response.data.access_token || response.data.token;
        if (tok) localStorage.setItem('token', tok);
        if (response.data.user) localStorage.setItem('user', JSON.stringify(response.data.user));
        return response.data;
    } catch (error) {
        const errorMessage = error.response?.data?.detail || error.message || 'Login failed. Please try again.';
        throw new Error(errorMessage);
    }
};

// Dashboard Data Fetch
export const getDashboardData = async () => {
    return await api.get('/api/dashboard');
};

// Streaming utilities
export class EventSourceManager {
    constructor() {
        this.activeStreams = new Map();
    }

    createEventSource(url, onMessage, onError, onComplete) {
        const streamId = Math.random().toString(36).substr(2, 9);
        const eventSource = new EventSource(url);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data, streamId);
                
                if (data.type === 'complete' || data.type === 'disconnect') {
                    this.closeStream(streamId);
                    if (onComplete) onComplete(streamId);
                }
            } catch (error) {
                console.error('Error parsing SSE data:', error);
                if (onError) onError(error, streamId);
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            if (onError) onError(error, streamId);
            this.closeStream(streamId);
        };

        this.activeStreams.set(streamId, eventSource);
        return streamId;
    }

    closeStream(streamId) {
        const eventSource = this.activeStreams.get(streamId);
        if (eventSource) {
            eventSource.close();
            this.activeStreams.delete(streamId);
        }
    }

    closeAllStreams() {
        this.activeStreams.forEach((eventSource, streamId) => {
            eventSource.close();
        });
        this.activeStreams.clear();
    }
}

export const eventSourceManager = new EventSourceManager();

// Mock Test API with streaming
export const generateMockTest = async (category, difficulty, stream = false) => {
    if (stream) {
        return `/api/mock/generate-stream?category=${encodeURIComponent(category)}&difficulty=${encodeURIComponent(difficulty)}`;
    }
    return await longRunningApi.post('/api/mock/generate', { category, difficulty });
};

export const submitMockAnswer = async (sessionId, questionId, answer) => {
    return await longRunningApi.post('/api/mock/answer', { sessionId, questionId, answer });
};

// Interview API with streaming
export const startInterview = async (role, type, stream = false) => {
    if (stream) {
        return `/api/interview/start-stream?role=${encodeURIComponent(role)}&type=${encodeURIComponent(type)}`;
    }
    return await longRunningApi.post('/api/interview/start', { role, type });
};

export const sendInterviewMessage = async (sessionId, message, stream = false) => {
    if (stream) {
        return `/api/interview/chat-stream?session_id=${sessionId}&message=${encodeURIComponent(message)}`;
    }
    return await longRunningApi.post('/api/interview/chat', { session_id: sessionId, message });
};

// English Practice API with streaming
export const startEnglishSession = async (topic, stream = false) => {
    if (stream) {
        return `/api/english/start-session-stream?topic=${encodeURIComponent(topic)}`;
    }
    return await longRunningApi.post('/api/english/start-session', { topic });
};

export const sendEnglishMessage = async (sessionId, message, stream = false) => {
    if (stream) {
        return `/api/english/chat-stream?session_id=${sessionId}&message=${encodeURIComponent(message)}`;
    }
    return await longRunningApi.post('/api/english/chat', { session_id: sessionId, message });
};

// Helper function to determine if endpoint should use streaming
export const shouldUseStreaming = (endpointType) => {
    const streamingEndpoints = ['interview', 'english', 'mock'];
    return streamingEndpoints.includes(endpointType);
};

export default api;