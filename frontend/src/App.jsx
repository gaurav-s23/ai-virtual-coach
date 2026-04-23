import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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

const ProtectedRoute = ({ children }) => {
    const token = localStorage.getItem('token');
    
    if (!token) {
        return <Navigate to="/auth" />;
    }
    
    // Basic JWT token validation (check if token is properly formatted)
    try {
        const parts = token.split('.');
        if (parts.length !== 3) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            return <Navigate to="/auth" />;
        }
        
        // Check if token is expired (basic check)
        const payload = JSON.parse(atob(parts[1]));
        const currentTime = Date.now() / 1000;
        if (payload.exp && payload.exp < currentTime) {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            return <Navigate to="/auth" />;
        }
        
        return children;
    } catch (error) {
        console.error('Token validation failed:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        return <Navigate to="/auth" />;
    }
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