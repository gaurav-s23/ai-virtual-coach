import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { generateMockTest, eventSourceManager } from '../services/api';
import { 
    Zap, BrainCircuit, Loader2, Target, Clock, ChevronLeft, 
    ChevronRight, Send, BarChart3, ArrowLeft, Square, AlertTriangle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function MockTest() {
    const navigate = useNavigate();
    let user = null;
    try { user = JSON.parse(localStorage.getItem('user') || 'null'); } catch {}

    // --- APP STATES ---
    const [testState, setTestState] = useState('selection'); 
    const [category, setCategory] = useState('');
    const [questions, setQuestions] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [userAnswers, setUserAnswers] = useState({}); 
    const [status, setStatus] = useState({}); 
    const [timeLeft, setTimeLeft] = useState(1200); 
    const [loading, setLoading] = useState(false);
    const [cacheHit, setCacheHit] = useState(false);
    const [showEndDialog, setShowEndDialog] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [sessionStarted, setSessionStarted] = useState(false);

    // --- 1. START TEST (With Streaming Support) ---
    const startTest = async (cat, forceNew = false) => {
        setCategory(cat);
        setCacheHit(!forceNew);
        setLoading(true);
        setTestState('generating'); // New state for streaming generation

        try {
            // Generate session ID first
            const newSessionId = `mock_${Date.now()}`;
            setSessionId(newSessionId);
            setSessionStarted(true);

            // Mark session as started
            await api.post('/api/mock/start-session', {
                session_id: newSessionId,
                category: cat
            });

            // Use streaming API for question generation
            const streamUrl = generateMockTest(cat, 'medium', true);
            
            // Create streaming connection
            const streamId = eventSourceManager.createEventSource(
                `${api.API_BASE}${streamUrl}&session_id=${newSessionId}`,
                (data, streamId) => {
                    if (data.type === 'content' && data.chunk) {
                        // Accumulate streaming content
                        setQuestions(prev => {
                            try {
                                const newQuestion = JSON.parse(data.chunk);
                                return [...prev, newQuestion];
                            } catch {
                                return prev;
                            }
                        });
                    } else if (data.type === 'complete') {
                        // Generation complete
                        setTestState('testing');
                        setCurrentIndex(0);
                        setTimeLeft(1200);
                        setLoading(false);
                    } else if (data.type === 'error') {
                        console.error('Streaming error:', data.error);
                        alert(`Failed to generate quiz: ${data.error}`);
                        setTestState('selection');
                        setLoading(false);
                    }
                },
                (error, streamId) => {
                    console.error('SSE error:', error);
                    alert(`Connection error: ${error.message || 'Unknown error'}`);
                    setTestState('selection');
                    setLoading(false);
                },
                (streamId) => {
                    console.log('Stream completed:', streamId);
                }
            );

        } catch (e) {
            console.error("Network Error:", e);
            const detail = e.response?.data?.detail || e.message || "Server error";
            const status = e.response?.status || "network";
            alert(`Quiz failed (${status}): ${detail}`);
            setTestState('selection');
            setLoading(false);
        }
    };

    // --- Abandoned Session Tracking ---
    const markSessionAbandoned = async () => {
        if (sessionStarted && sessionId) {
            try {
                await api.post('/api/mock/abandon-session', {
                    session_id: sessionId,
                    abandoned_at: new Date().toISOString()
                });
            } catch (error) {
                console.error('Failed to mark session as abandoned:', error);
            }
        }
    };

    useEffect(() => {
        const handleBeforeUnload = (e) => {
            if (sessionStarted) {
                markSessionAbandoned();
                e.preventDefault();
                e.returnValue = '';
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
            if (sessionStarted) {
                markSessionAbandoned();
            }
        };
    }, [sessionStarted, sessionId]);

    // --- End Test with Confirmation ---
    const handleEndTest = () => {
        setShowEndDialog(true);
    };

    const confirmEndTest = async () => {
        setShowEndDialog(false);
        if (sessionStarted && sessionId) {
            try {
                await api.post('/api/mock/end-session', {
                    session_id: sessionId,
                    ended_at: new Date().toISOString(),
                    user_answers: userAnswers,
                    status: 'completed'
                });
            } catch (error) {
                console.error('Failed to end session properly:', error);
            }
        }
        submitTest();
    };

    const cancelEndTest = () => {
        setShowEndDialog(false);
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
                await api.post(`/api/user/update-stats/${user.id}`, {
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

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
                        {['Quant', 'Verbal', 'Reasoning', 'Coding'].map((cat) => (
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

    // 2. GENERATING STATE (Streaming)
    if (testState === 'generating') {
        return (
            <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center p-6 font-sans relative overflow-hidden">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-cyan-600/10 blur-[140px] rounded-full animate-pulse" />
                
                <div className="max-w-2xl w-full space-y-12 relative z-10">
                    <div className="text-center">
                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="inline-flex p-3 bg-cyan-600/20 rounded-2xl mb-4 border border-cyan-500/30">
                            <BrainCircuit className="text-cyan-400" fill="currentColor" />
                        </motion.div>
                        <h1 className="text-4xl font-black tracking-tighter italic uppercase">Generating <span className="text-cyan-400">{category}</span> Questions</h1>
                        <p className="text-slate-500 text-[10px] font-black uppercase tracking-[0.5em] mt-4">AI is creating personalized assessment</p>
                    </div>

                    <div className="bg-white/[0.02] border border-white/10 rounded-[3rem] p-12 backdrop-blur-3xl">
                        <div className="flex items-center justify-center mb-8">
                            <Loader2 className="animate-spin text-cyan-400" size={48} />
                        </div>
                        
                        <div className="space-y-4">
                            <div className="flex justify-between items-center">
                                <span className="text-sm text-gray-400">Questions Generated</span>
                                <span className="text-cyan-400 font-mono font-bold">{questions.length}/10</span>
                            </div>
                            
                            <div className="w-full h-2 bg-black/40 rounded-full overflow-hidden">
                                <motion.div 
                                    initial={{ width: 0 }} 
                                    animate={{ width: `${(questions.length / 10) * 100}%` }}
                                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full" 
                                />
                            </div>
                            
                            <p className="text-center text-gray-500 text-sm animate-pulse">
                                Using advanced AI models to create challenging questions...
                            </p>
                        </div>
                        
                        <div className="mt-8 flex justify-center">
                            <button
                                onClick={() => {
                                    eventSourceManager.closeAllStreams();
                                    setTestState('selection');
                                    setQuestions([]);
                                    setSessionStarted(false);
                                }}
                                className="px-6 py-3 bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 hover:text-red-300 rounded-2xl transition-all"
                            >
                                Cancel Generation
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // 3. TESTING INTERFACE (70/30)
    const currentQ = questions[currentIndex];
    if (!currentQ) return null;

    return (
        <div className="h-screen bg-[#010409] text-slate-300 font-sans flex overflow-hidden">
            {/* Fixed Header with Back/End Buttons */}
            <div className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-xl border-b border-white/10 px-6 py-4">
                <div className="flex justify-between items-center max-w-full">
                    <button
                        onClick={() => {
                            markSessionAbandoned();
                            navigate('/dashboard');
                        }}
                        className="px-4 py-2.5 rounded-2xl bg-gray-600/20 hover:bg-gray-600/30 border border-gray-500/30 text-gray-400 hover:text-gray-300 transition-all flex items-center gap-2"
                    >
                        <ArrowLeft size={16} />
                        <span className="text-xs font-black uppercase tracking-widest">Back</span>
                    </button>
                    <div className="flex items-center gap-4">
                        <div className={`px-5 py-2.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 transition-colors ${timeLeft < 300 ? 'text-red-500 border-red-500/40 bg-red-500/5 animate-pulse' : 'border-white/10 bg-white/5'}`}>
                            <Clock size={18} />
                            <span className="font-mono text-lg font-black">{formatTime(timeLeft)}</span>
                        </div>
                        <button
                            onClick={handleEndTest}
                            className="px-4 py-2.5 rounded-2xl bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 hover:text-red-300 transition-all flex items-center gap-2"
                        >
                            <Square size={16} />
                            <span className="text-xs font-black uppercase tracking-widest">End Test</span>
                        </button>
                    </div>
                </div>
            </div>

            {/* 70% MAIN HUB */}
            <div className="flex-1 flex flex-col p-10 pt-24 relative">
                <header className="flex justify-between items-center mb-10">
                    <div className="flex items-center gap-4">
                        <div className="p-2 bg-cyan-600 rounded-xl shadow-[0_0_15px_rgba(6,182,212,0.4)]">
                            <Target size={20} className="text-white" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black text-cyan-500 uppercase tracking-widest leading-none mb-1">Assessment Engine</p>
                            <h2 className="text-2xl font-black text-white italic">{category} Mock Test</h2>
                        </div>
                    </div>
                    <div className="px-6 py-3 bg-white/5 border rounded-2xl font-mono text-2xl shadow-inner flex items-center gap-3 transition-colors">
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

            {/* Confirmation Dialog */}
            <AnimatePresence>
                {showEndDialog && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6"
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            className="bg-white/[0.03] border border-white/10 rounded-[3rem] p-8 max-w-md w-full backdrop-blur-3xl shadow-2xl"
                        >
                            <div className="flex items-center gap-4 mb-6">
                                <div className="p-3 bg-red-500/20 rounded-full text-red-500">
                                    <AlertTriangle size={24} />
                                </div>
                                <h3 className="text-2xl font-bold text-white">End Test?</h3>
                            </div>
                            <p className="text-gray-300 mb-8 leading-relaxed">
                                Are you sure you want to end the test? Your progress will be submitted and you won't be able to continue.
                            </p>
                            <div className="flex gap-4">
                                <button
                                    onClick={cancelEndTest}
                                    className="flex-1 px-6 py-3 bg-gray-600/20 hover:bg-gray-600/30 border border-gray-500/30 text-gray-400 hover:text-gray-300 rounded-2xl font-bold transition-all"
                                >
                                    No, Continue
                                </button>
                                <button
                                    onClick={confirmEndTest}
                                    className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold transition-all"
                                >
                                    Yes, End Test
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

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