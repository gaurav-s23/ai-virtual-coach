import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios'; // 👈 1. Yeh import miss tha
import { ShieldCheck, Mail, Lock } from 'lucide-react';

export default function Auth() {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // 👈 2. Directly calling the URL to ensure connection
            const response = await axios.post("http://127.0.0.1:8000/api/login", {
                email: email,
                password: password
            });
            
            if (response.data) {
                console.log("Success:", response.data);
                localStorage.setItem('user', JSON.stringify(response.data.user));
                alert("Login Successful!");
                navigate('/'); 
                window.location.reload(); 
            }
        } catch (error) {
            // 👈 3. Bullet-proof error handling
            console.error("Auth Error:", error);
            if (error.response) {
                // Backend ne response bheja (e.g. 400 or 422 error)
                alert("Login Failed: " + (error.response.data.detail || "Invalid Credentials"));
            } else {
                // Network issue ya Backend band hai
                alert("Cannot connect to server. Make sure your Python backend is running on port 8000!");
            }
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-slate-950 px-4">
            <div className="w-full max-w-md p-8 bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl shadow-2xl">
                <div className="text-center mb-10">
                    <ShieldCheck className="w-12 h-12 text-blue-500 mx-auto mb-4" />
                    <h2 className="text-3xl font-bold text-white">{isLogin ? 'Welcome Back' : 'Create Account'}</h2>
                    <p className="text-gray-400 mt-2 text-sm">Join the elite AI Virtual coaching program.</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="relative">
                        <Mail className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                        <input 
                            type="email" placeholder="Email Address" required
                            className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-blue-500 outline-none transition-all"
                            onChange={(e) => setEmail(e.target.value)}
                        />
                    </div>
                    <div className="relative">
                        <Lock className="absolute left-3 top-3 w-5 h-5 text-gray-500" />
                        <input 
                            type="password" placeholder="Password" required
                            className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-blue-500 outline-none transition-all"
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-900/40 transition-all">
                        {isLogin ? 'Sign In' : 'Sign Up'}
                    </button>
                </form>

                <p className="text-center text-gray-500 mt-8 text-sm">
                    {isLogin ? "Don't have an account?" : "Already have an account?"}
                    <button onClick={() => setIsLogin(!isLogin)} className="ml-2 text-blue-400 font-semibold underline">
                        {isLogin ? 'Register Now' : 'Login Here'}
                    </button>
                </p>
            </div>
        </div>
    );
}