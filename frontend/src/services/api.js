import axios from 'axios';

const API_URL = (import.meta?.env?.VITE_API_URL ?? "").replace(/\/$/, ""); // Build-time env for Docker/production

const api = axios.create({
    baseURL: API_URL,
    headers: { "Content-Type": "application/json" }
});

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
    const token = localStorage.getItem('token');
    return await api.get('/api/dashboard', {
        headers: { Authorization: `Bearer ${token}` }
    });
};

export default api;