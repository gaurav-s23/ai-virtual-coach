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
    const token = localStorage.getItem('token');
    const [isValidating, setIsValidating] = useState(true);
    const [isAuthenticated, setIsAuthenticated] = useState(false);

    useEffect(() => {
        const validateToken = async () => {
            if (!token) {
                setIsValidating(false);
                setIsAuthenticated(false);
                return;
            }

            try {
                // Use server-side token verification
                const response = await api.post('/auth/verify-token', { token });
                
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
            } finally {
                setIsValidating(false);
            }
        };

        validateToken();
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
    const adminToken = localStorage.getItem('admin_token');
    
    if (!adminToken) {
        return <Navigate to="/admin/login" />;
    }
    
    // Basic admin token validation
    try {
        const parts = adminToken.split('.');
        if (parts.length !== 3) {
            localStorage.removeItem('admin_token');
            return <Navigate to="/admin/login" />;
        }
        
        // Check if token is expired
        const payload = JSON.parse(atob(parts[1]));
        const currentTime = Date.now() / 1000;
        if (payload.exp && payload.exp < currentTime) {
            localStorage.removeItem('admin_token');
            return <Navigate to="/admin/login" />;
        }
        
        // Check if role is admin
        if (payload.role !== 'admin') {
            localStorage.removeItem('admin_token');
            return <Navigate to="/admin/login" />;
        }
        
        return children;
    } catch (error) {
        console.error('Admin token validation failed:', error);
        localStorage.removeItem('admin_token');
        return <Navigate to="/admin/login" />;
    }
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