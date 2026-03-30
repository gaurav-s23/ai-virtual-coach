import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, Mail, Lock, Loader2, ChevronRight, ShieldCheck, Sparkles } from 'lucide-react';
import axios from 'axios';

export default function Auth() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('idle'); 
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus('syncing');

    try {
      const response = await axios.post('http://127.0.0.1:8000/api/login', { 
        email, 
        password 
      });
      
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setStatus('success');

      setTimeout(() => {
        // Ensure this matches the route in your App.jsx
        navigate('/dashboard'); 
      }, 1500);
      
    } catch (error) {
      setStatus('idle');
      console.error("Login Error:", error);
      alert("Neural Sync Failed: " + (error.response?.data?.detail || "Invalid Credentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#030303] text-slate-200 flex items-center justify-center p-6 relative overflow-hidden font-sans">
      
      {/* --- FIX 1: Removed noise.svg to prevent 403 error --- */}
      <div className="fixed inset-0 z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-purple-600/10 blur-[120px] rounded-full animate-pulse delay-700" />
        {/* CSS-only noise effect instead of external SVG */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* LOGO AREA */}
        <div className="flex flex-col items-center mb-10 text-center">
          <div className="p-4 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-3xl shadow-[0_0_30px_rgba(37,99,235,0.3)] mb-6">
            <Zap size={32} className="text-white" fill="white" />
          </div>
          <h1 className="text-4xl font-black tracking-tighter text-white uppercase mb-2">
            ai_virtual<span className="text-blue-500">coach</span>
          </h1>
          <p className="text-gray-500 font-medium tracking-wide text-sm uppercase italic">Initialize Neural Career Simulation</p>
        </div>

        {/* LOGIN CARD */}
        <div className="bg-white/[0.02] border border-white/10 backdrop-blur-3xl rounded-[2.5rem] p-10 shadow-2xl relative overflow-hidden group">
            {/* Animated Border Beam */}
            <div className="absolute -inset-[1px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent rounded-[2.5rem] opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />

            <form onSubmit={handleLogin} className="relative z-10 space-y-6">
                
                {/* EMAIL INPUT */}
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] ml-2 font-mono">Neural ID (Email)</label>
                    <div className="relative group/input">
                        <Mail className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within/input:text-blue-500 transition-colors" size={18} />
                        <input 
                            type="email" 
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="cadet@neuralai.com"
                            className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-5 pl-14 pr-6 text-sm outline-none focus:border-blue-500/50 focus:bg-white/[0.06] transition-all placeholder:text-gray-700"
                        />
                    </div>
                </div>

                {/* PASSWORD INPUT */}
                <div className="space-y-2">
                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-[0.2em] ml-2 font-mono">Access Key</label>
                    <div className="relative group/input">
                        <Lock className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-600 group-focus-within/input:text-blue-500 transition-colors" size={18} />
                        <input 
                            type="password" 
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            className="w-full bg-white/[0.03] border border-white/10 rounded-2xl py-5 pl-14 pr-6 text-sm outline-none focus:border-blue-500/50 focus:bg-white/[0.06] transition-all placeholder:text-gray-700"
                        />
                    </div>
                </div>

                {/* SUBMIT BUTTON */}
                <button 
                    type="submit" 
                    disabled={loading || status === 'success'}
                    className="w-full relative group/btn overflow-hidden bg-blue-600 py-5 rounded-2xl font-black text-xs uppercase tracking-[0.2em] text-white transition-all hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_30px_rgba(37,99,235,0.3)] disabled:opacity-50"
                >
                    <AnimatePresence mode="wait">
                        {status === 'idle' && (
                            <motion.div key="idle" className="flex items-center justify-center gap-2">
                                JOIN SIMULATION <ChevronRight size={16} />
                            </motion.div>
                        )}
                        {status === 'syncing' && (
                            <motion.div key="syncing" className="flex items-center justify-center gap-2">
                                <Loader2 className="animate-spin" size={18} /> SYNCING...
                            </motion.div>
                        )}
                        {status === 'success' && (
                            <motion.div key="success" className="flex items-center justify-center gap-2 text-emerald-300">
                                <ShieldCheck size={18} /> ACCESS GRANTED
                            </motion.div>
                        )}
                    </AnimatePresence>
                </button>
            </form>
        </div>

        {/* FOOTER INFO */}
        <div className="mt-10 flex items-center justify-center gap-6 opacity-40">
            <div className="flex items-center gap-2">
                <ShieldCheck size={14} />
                <span className="text-[10px] font-bold uppercase tracking-widest font-mono">Encrypted</span>
            </div>
            <div className="w-1 h-1 bg-gray-600 rounded-full" />
            <div className="flex items-center gap-2">
                <Sparkles size={14} />
                <span className="text-[10px] font-bold uppercase tracking-widest font-mono">v2.5 Neural Core</span>
            </div>
        </div>
      </motion.div>

      {/* --- FIX 2: Removed "jsx" and "global" attributes from style tag --- */}
      <style>{`
        @keyframes shimmer {
          100% { transform: translateX(100%); }
        }
        .group-hover\/btn\:animate-shimmer {
          animation: shimmer 1.5s infinite;
        }
      `}</style>
    </div>
  );
}