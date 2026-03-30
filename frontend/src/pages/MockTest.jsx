import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
    Zap, BrainCircuit, Loader2, Target, Clock, ChevronLeft, 
    ChevronRight, Flag, Send, BarChart3, Trophy, ArrowLeft, XCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function MockTest() {
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user'));

    // --- APP STATES ---
    const [testState, setTestState] = useState('selection'); 
    const [category, setCategory] = useState('');
    const [questions, setQuestions] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [userAnswers, setUserAnswers] = useState({}); 
    const [status, setStatus] = useState({}); 
    const [timeLeft, setTimeLeft] = useState(1200); 
    const [loading, setLoading] = useState(false);

    // --- 1. START TEST (Synced with Backend Fail-safe Logic) ---
    const startTest = async (cat) => {
        setCategory(cat);
        setLoading(true);

        try {
            const res = await axios.post("http://127.0.0.1:8000/api/generate-quiz", { 
                category: cat 
            });

            if (res.data && Array.isArray(res.data) && res.data.length > 0) {
                setQuestions(res.data);
                setTestState('testing');
                setCurrentIndex(0);
                setTimeLeft(1200);
            } else {
                alert("Neural Engine failed to synthesize questions. Retrying...");
            }
        } catch (e) {
            console.error("Network Error:", e);
            alert(`Simulation Error: ${e.response?.data?.detail || "Check server connectivity"}`);
        } finally {
            setLoading(false);
        }
    };

    // --- 2. TIMER LOGIC ---
    useEffect(() => {
        let timer;
        if (testState === 'testing' && timeLeft > 0) {
            timer = setInterval(() => setTimeLeft(prev => prev - 1), 1000);
        } else if (timeLeft === 0 && testState === 'testing') {
            submitTest();
        }
        return () => clearInterval(timer);
    }, [timeLeft, testState]);

    const formatTime = (s) => `${Math.floor(s/60)}:${(s%60).toString().padStart(2, '0')}`;

    // --- 3. PERSISTENCE LOGIC (Update Dashboard & DB) ---
    const submitTest = async () => {
        const { score, total } = calculateScore();
        setLoading(true);

        try {
            // Update Database Stats
            if (user?.id) {
                await axios.post(`http://127.0.0.1:8000/api/user/update-stats/${user.id}`, {
                    score: score,
                    type: "mock"
                });
            }

            // Sync with Frontend Dashboard State
            navigate('/dashboard', { 
                state: { 
                    mockResult: { score, total } 
                } 
            });

        } catch (e) {
            console.error("Failed to sync score:", e);
            setTestState('result'); // Still show result even if DB sync fails
        } finally {
            setLoading(false);
        }
    };

    const handleAnswer = (option) => {
        const qId = questions[currentIndex].id;
        setUserAnswers(prev => ({ ...prev, [qId]: option }));
        if (status[qId] !== 'review') setStatus(prev => ({ ...prev, [qId]: 'answered' }));
    };

    const toggleReview = () => {
        const qId = questions[currentIndex].id;
        setStatus(prev => ({ ...prev, [qId]: status[qId] === 'review' ? 'answered' : 'review' }));
    };

    const calculateScore = () => {
        let correct = 0;
        questions.forEach(q => {
            if (userAnswers[q.id] === q.answer) correct++;
        });
        return { score: correct, total: questions.length };
    };

    // --- UI RENDERING ---

    // 1. SELECTION HUD
    if (testState === 'selection') {
        return (
            <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center p-6 font-sans relative overflow-hidden">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-cyan-600/10 blur-[140px] rounded-full animate-pulse" />
                
                <div className="max-w-4xl w-full space-y-12 relative z-10">
                    <div className="text-center">
                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="inline-flex p-3 bg-cyan-600/20 rounded-2xl mb-4 border border-cyan-500/30">
                            <Zap className="text-cyan-400" fill="currentColor" />
                        </motion.div>
                        <h1 className="text-6xl font-black tracking-tighter italic uppercase">Neural <span className="text-cyan-400">Mock hub</span></h1>
                        <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.5em] mt-4">AI Assessment Protocol v2.5</p>
                    </div>

                    <div className="grid md:grid-cols-3 gap-8">
                        {['Quant', 'Verbal', 'Reasoning'].map((cat) => (
                            <motion.button 
                                key={cat}
                                whileHover={{ y: -8, scale: 1.02 }}
                                onClick={() => startTest(cat)}
                                disabled={loading}
                                className="group relative p-10 bg-white/[0.02] border border-white/10 rounded-[3rem] hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-all text-left overflow-hidden backdrop-blur-3xl"
                            >
                                <BrainCircuit className="text-cyan-400 mb-6" size={32} />
                                <h3 className="text-3xl font-bold tracking-tight mb-2">{cat}</h3>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest leading-none group-hover:text-cyan-400 transition-colors">Initialize Matrix</p>
                                
                                {loading && category === cat && (
                                    <div className="absolute inset-0 bg-black/80 flex flex-col items-center justify-center backdrop-blur-sm">
                                        <Loader2 className="animate-spin text-cyan-400 mb-2" size={32} />
                                        <span className="text-[9px] font-black tracking-[0.3em] animate-pulse">EXTRACTING DATA...</span>
                                    </div>
                                )}
                            </motion.button>
                        ))}
                    </div>
                </div>
            </div>
        );
    }

    // 2. TESTING INTERFACE (70/30)
    const currentQ = questions[currentIndex];
    if (!currentQ) return null;

    return (
        <div className="h-screen bg-[#010409] text-slate-300 font-sans flex overflow-hidden">
            {/* 70% MAIN HUB */}
            <div className="flex-1 flex flex-col p-10 relative">
                <header className="flex justify-between items-center mb-10">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-cyan-600 rounded-xl shadow-[0_0_15px_rgba(6,182,212,0.4)]">
                            <Target size={20} className="text-white" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-cyan-500 uppercase tracking-widest leading-none mb-1">Assessment Engine</p>
                            <h2 className="font-bold text-white uppercase tracking-tighter text-lg">{category} node active</h2>
                        </div>
                    </div>
                    <div className={`px-6 py-3 bg-white/5 border rounded-2xl font-mono text-2xl shadow-inner flex items-center gap-3 transition-colors ${timeLeft < 300 ? 'text-red-500 border-red-500/40 animate-pulse' : 'text-cyan-400 border-white/10'}`}>
                        <Clock size={20} />
                        {formatTime(timeLeft)}
                    </div>
                </header>

                <div className="flex-1 bg-white/[0.02] border border-white/5 rounded-[3rem] p-12 overflow-y-auto scrollbar-hide backdrop-blur-3xl shadow-2xl relative">
                    <span className="text-[9px] font-black text-slate-600 uppercase tracking-[0.4em]">Memory Slot {currentIndex + 1} / {questions.length}</span>
                    <h1 className="text-3xl font-bold mt-6 mb-12 text-white leading-tight italic tracking-tight">"{currentQ.question}"</h1>

                    <div className="grid gap-4 max-w-4xl">
                        {currentQ.options.map((opt, i) => {
                            const isSelected = userAnswers[currentQ.id] === opt;
                            return (
                                <button 
                                    key={i} 
                                    onClick={() => handleAnswer(opt)}
                                    className={`group p-6 rounded-2xl border text-left transition-all duration-300 ${isSelected ? 'bg-cyan-600 border-cyan-400 text-white shadow-[0_0_20px_rgba(6,182,212,0.3)] scale-[1.01]' : 'bg-white/[0.02] border-white/5 hover:border-cyan-500/40'}`}
                                >
                                    <div className="flex items-center gap-5">
                                        <span className={`w-8 h-8 rounded-lg flex items-center justify-center font-black text-[10px] ${isSelected ? 'bg-white/20' : 'bg-white/5'}`}>{String.fromCharCode(65 + i)}</span>
                                        <span className="text-lg font-medium tracking-tight italic">{opt}</span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>

                <footer className="mt-8 flex justify-between items-center px-4">
                    <button disabled={currentIndex === 0} onClick={() => setCurrentIndex(prev => prev - 1)} className="p-5 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-all disabled:opacity-5"><ChevronLeft/></button>
                    <div className="flex gap-4">
                        <button onClick={toggleReview} className={`px-10 py-4 rounded-2xl font-black text-[10px] uppercase tracking-widest transition-all ${status[currentQ.id] === 'review' ? 'bg-yellow-500 text-black' : 'bg-white/5 border border-white/10 text-yellow-500'}`}>Mark For Review</button>
                        <button onClick={submitTest} disabled={loading} className="px-10 py-4 bg-cyan-600 text-white rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-xl shadow-cyan-600/20 hover:bg-cyan-500 flex items-center gap-3">
                            {loading ? <Loader2 className="animate-spin" size={18}/> : <>FINALIZE ASSESSMENT <Send size={14}/></>}
                        </button>
                    </div>
                    <button disabled={currentIndex === questions.length - 1} onClick={() => setCurrentIndex(prev => prev + 1)} className="p-5 bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-all disabled:opacity-5"><ChevronRight/></button>
                </footer>
            </div>

            {/* 30% SIDEBAR NAVIGATION */}
            <aside className="w-80 bg-black/40 backdrop-blur-md border-l border-white/5 p-10 flex flex-col relative z-10">
                <div className="mb-10">
                    <h3 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-500 mb-8 text-center">Neural Matrix</h3>
                    <div className="grid grid-cols-4 gap-3">
                        {questions.map((q, idx) => (
                            <button 
                                key={q.id} 
                                onClick={() => setCurrentIndex(idx)}
                                className={`aspect-square rounded-xl border text-[11px] font-black transition-all ${currentIndex === idx ? 'ring-2 ring-white scale-110 z-10' : ''} ${
                                    status[q.id] === 'answered' ? 'bg-cyan-600 border-cyan-400 text-white shadow-lg' : 
                                    status[q.id] === 'review' ? 'bg-yellow-500 border-yellow-400 text-black' : 
                                    'bg-white/5 border-white/10 text-slate-600'
                                }`}
                            >
                                {idx + 1}
                            </button>
                        ))}
                    </div>
                </div>
                
                <div className="mt-auto bg-white/[0.02] p-8 rounded-[2.5rem] border border-white/5">
                   <div className="flex items-center gap-3 text-[10px] font-black uppercase text-slate-500 tracking-widest mb-6"><BarChart3 size={14}/> Node Legend</div>
                   <div className="space-y-4">
                      <div className="flex items-center gap-4 text-[11px] font-bold text-white"><div className="w-3 h-3 rounded bg-cyan-600 shadow-[0_0_10px_rgba(6,182,212,0.6)]" /> Attempted</div>
                      <div className="flex items-center gap-4 text-[11px] font-bold text-white"><div className="w-3 h-3 rounded bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.3)]" /> Review Mode</div>
                      <div className="flex items-center gap-4 text-[11px] font-bold text-white"><div className="w-3 h-3 rounded bg-white/5" /> Unseen Node</div>
                   </div>
                </div>
            </aside>
        </div>
    );
}