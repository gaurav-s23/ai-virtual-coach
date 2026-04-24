import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Home from './pages/Home';
import Auth from './pages/Auth';
import InterviewSetup from './pages/InterviewSetup'; 
import LiveInterview from './pages/LiveInterview';   
import Dashboard from './pages/Dashboard';           
import MockTest from './pages/MockTest'; 
import EnglishPractice from './pages/EnglishPractice';
import Evaluation from './pages/Evaluation';
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import AdminPanel from './pages/AdminPanel';
import api from './services/api';

const ProtectedRoute = ({ children }) => {
    const [token, setToken] = useState(null);
    const [isValidating, setIsValidating] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    // Synchronous check for immediate token presence
    const currentToken = localStorage.getItem('token');
    if (!currentToken) {
        localStorage.removeItem('user');
        return <Navigate to="/auth" replace />;
    }

    useEffect(() => {
        const validateToken = async () => {
            const currentToken = localStorage.getItem('token');
            if (!currentToken) {
                setIsValidating(false);
                setIsAuthenticated(false);
                return;
            }

            try {
                // Use server-side token verification
                const response = await api.post('/auth/verify-token', { token: currentToken });
                
                if (response.data.valid) {
                    // Update user info in localStorage if needed
                    const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
                    if (!currentUser.id || currentUser.id !== response.data.user.id) {
                        localStorage.setItem('user', JSON.stringify(response.data.user));
                    }
                    setIsAuthenticated(true);
                } else {
                    // Token is invalid, clear storage
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    setIsAuthenticated(false);
                }
            } catch (error) {
                console.error('Server-side token validation failed:', error);
                // Clear storage on any validation error
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                setIsAuthenticated(false);
                // Show user-friendly error message
                alert('Session validation failed. Please try logging in again.');
            } finally {
                setIsValidating(false);
            }
        };

        validateToken();
    }, []);

    useEffect(() => {
        const refreshToken = async () => {
            const currentToken = localStorage.getItem('token');
            if (!currentToken) {
                setIsValidating(false);
                setIsAuthenticated(false);
                return;
            }

            try {
                // Use server-side token refresh
                const response = await api.post('/auth/refresh-token', { token: currentToken });
                
                if (response.data.valid) {
                    // Update token in localStorage if needed
                    const newToken = response.data.token;
                    localStorage.setItem('token', newToken);
                    setToken(newToken);
                } else {
                    // Token is invalid, clear storage
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    setIsAuthenticated(false);
                }
            } catch (error) {
                console.error('Server-side token refresh failed:', error);
                // Clear storage on any validation error
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                setIsAuthenticated(false);
                // Show user-friendly error message
                alert('Session validation failed. Please try logging in again.');
            }
        };

        const intervalId = setInterval(refreshToken, 1000 * 60 * 5); // Refresh token every 5 minutes

        return () => clearInterval(intervalId);
    }, [token]);

    // Show loading state during validation
    if (isValidating) {
        return (
            <div style={{ 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                height: '100vh',
                fontSize: '18px',
                color: '#666'
            }}>
                Validating session...
            </div>
        );
    }

    // Redirect to auth if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/auth" replace />;
    }

    // Render children if authenticated
    return children;
};

const AdminProtectedRoute = ({ children }) => {
    const [isValidating, setIsValidating] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    useEffect(() => {
        const validateAdminToken = async () => {
            const adminToken = localStorage.getItem('admin_token');
            
            if (!adminToken) {
                setIsValidating(false);
                setIsAuthenticated(false);
                return;
            }

            try {
                // Server-side admin token validation
                const response = await api.post('/api/admin/verify-token', { token: adminToken });
                
                if (response.data.valid && response.data.role === 'admin') {
                    setIsAuthenticated(true);
                } else {
                    localStorage.removeItem('admin_token');
                    setIsAuthenticated(false);
                }
            } catch (error) {
                console.error('Admin token validation failed:', error);
                localStorage.removeItem('admin_token');
                setIsAuthenticated(false);
            } finally {
                setIsValidating(false);
            }
        };

        validateAdminToken();
    }, []);

    // Show loading state during validation
    if (isValidating) {
        return (
            <div style={{ 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                height: '100vh',
                fontSize: '18px',
                color: '#666'
            }}>
                Validating admin session...
            </div>
        );
    }

    // Redirect to admin login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/admin/login" replace />;
    }

    // Render children if authenticated
    return children;
};

function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* Public Routes */}
                <Route path="/auth" element={<Auth />} />
                <Route path="/" element={<Home />} />

                {/* --- INTERVIEW FLOW --- */}
                <Route path="/setup-interview" element={
                    <ProtectedRoute> <InterviewSetup /> </ProtectedRoute>
                } />
                
                <Route path="/live-interview" element={
                    <ProtectedRoute> <LiveInterview /> </ProtectedRoute>
                } />

                {/* --- MOCK TEST SECTION (Fixed path to /mock) --- */}
                <Route path="/mock" element={
                    <ProtectedRoute> <MockTest /> </ProtectedRoute>
                } />

                {/* --- ENGLISH PRACTICE SECTION (Fixed path to /english) --- */}
                <Route path="/english" element={
                    <ProtectedRoute> <EnglishPractice /> </ProtectedRoute>
                } />

                {/* --- USER DASHBOARD --- */}
                <Route path="/dashboard" element={
                    <ProtectedRoute> <Dashboard /> </ProtectedRoute>
                } />

                {/* --- EVALUATION PAGE --- */}
                <Route path="/evaluation/:sessionId" element={
                    <ProtectedRoute> <Evaluation /> </ProtectedRoute>
                } />

                <Route path="/admin/login" element={<AdminLogin />} />
                <Route path="/admin" element={
                    <AdminProtectedRoute> <AdminPanel /> </AdminProtectedRoute>
                } />

                {/* Fallback Route */}
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;