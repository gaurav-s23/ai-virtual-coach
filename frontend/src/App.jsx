import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import Auth from './pages/Auth';
import InterviewSetup from './pages/InterviewSetup'; 
import LiveInterview from './pages/LiveInterview';   
import Dashboard from './pages/Dashboard';           
import MockTest from './pages/MockTest'; 
import EnglishPractice from './pages/EnglishPractice';

const ProtectedRoute = ({ children }) => {
    const user = localStorage.getItem('user'); 
    return user ? children : <Navigate to="/auth" />;
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

                {/* Fallback Route */}
                <Route path="*" element={<Navigate to="/" />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;