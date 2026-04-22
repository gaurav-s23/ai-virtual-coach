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

const api = axios.create({
    baseURL: API_BASE,
    timeout: 10000, // 10 second timeout
});

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
        
        // Retry on server errors and some auth errors (might be transient)
        if ((status === 503 || status === 401 || status === 403) && config.__retryCount < 2) {
            config.__retryCount += 1;
            // For auth errors, wait a bit longer before retry
            const delay = (status === 401 || status === 403) ? 800 : 400;
            await new Promise((resolve) => setTimeout(resolve, delay * config.__retryCount));
            return api(config);
        }
        return Promise.reject(error);
    }
);

// Login Function
export const loginUser = async (credentials) => {
    const response = await api.post('/api/login', credentials);
    const tok = response.data.access_token || response.data.token;
    if (tok) localStorage.setItem('token', tok);
    if (response.data.user) localStorage.setItem('user', JSON.stringify(response.data.user));
    return response.data;
};

// Dashboard Data Fetch
export const getDashboardData = async () => {
    return await api.get('/api/dashboard');
};

export default api;