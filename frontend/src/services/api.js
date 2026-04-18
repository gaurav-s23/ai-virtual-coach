import axios from 'axios';

// In local dev, fallback to backend container port if env is missing.
const DEFAULT_API_URL = "http://localhost:8000";
export const API_BASE = (import.meta?.env?.VITE_API_URL ?? DEFAULT_API_URL).replace(/\/$/, "");

const api = axios.create({
    baseURL: API_BASE,
    headers: { "Content-Type": "application/json" }
});

api.interceptors.request.use((config) => {
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
        if (status === 503 && config.__retryCount < 2) {
            config.__retryCount += 1;
            await new Promise((resolve) => setTimeout(resolve, 400 * config.__retryCount));
            return api(config);
        }
        return Promise.reject(error);
    }
);

// Login Function
export const loginUser = async (credentials) => {
    const response = await api.post('/api/login', credentials);
    if (response.data.token) {
        localStorage.setItem('token', response.data.token);
    }
    return response.data;
};

// Dashboard Data Fetch
export const getDashboardData = async () => {
    return await api.get('/api/dashboard');
};

export default api;