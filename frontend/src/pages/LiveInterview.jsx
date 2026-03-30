import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Mic, Send, Loader2, Video, MicOff, MessageSquare, XCircle, Zap, ChevronRight, Volume2, Clock } from 'lucide-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';

export default function LiveInterview() {
    const location = useLocation();
    const navigate = useNavigate();
    
    // Initial data from setup
    const { questions: initialQuestions = [], intro = "System initialized.", context = "", role = "" } = location.state || {};

    const [questions, setQuestions] = useState(initialQuestions);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [messages, setMessages] = useState([{ role: 'ai', text: intro }]);
    const [userInput, setUserInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isAiSpeaking, setIsAiSpeaking] = useState(false); 
    const [phase, setPhase] = useState('primary'); // 'primary' or 'deepdive'
    const [timeLeft, setTimeLeft] = useState(1800); 
    const [performanceLog, setPerformanceLog] = useState([]);

    const videoRef = useRef(null);
    const chatEndRef = useRef(null);
    const recognitionRef = useRef(null);

    // D. AUTO-SCROLL LOGIC
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // TTS FUNCTION with Interruption Control
    const speak = (text, callback) => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        
        utterance.onstart = () => {
            setIsAiSpeaking(true);
            toggleListening(false); 
        };
        
        utterance.onend = () => {
            setIsAiSpeaking(false);
            if (callback) callback();
        };

        window.speechSynthesis.speak(utterance);
    };

    const askQuestion = (index, customQuestions = null) => {
        const qList = customQuestions || questions;
        const q = qList[index];
        if (!q) return;

        setMessages(prev => [...prev, { role: 'ai', text: q }]);
        speak(q, () => {
            toggleListening(true);
        });
    };

    // INTERVIEW LIFECYCLE
    useEffect(() => {
        // Camera setup
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
            .then(stream => { if (videoRef.current) videoRef.current.srcObject = stream; })
            .catch(err => console.error("Camera Blocked:", err));

        // STT setup
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = true;
            recognitionRef.current.interimResults = true;
            recognitionRef.current.onresult = (e) => {
                const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
                setUserInput(transcript);
            };
            recognitionRef.current.onend = () => setIsListening(false);
        }

        // Start Sequence
        speak(intro, () => {
            setTimeout(() => {
                if (questions.length > 0) askQuestion(0);
            }, 1000);
        });

        return () => {
            window.speechSynthesis.cancel();
            if (recognitionRef.current) recognitionRef.current.stop();
        };
    }, []);

    // Timer Logic
    useEffect(() => {
        if (timeLeft <= 0) return finishInterview("Simulation Time Limit Reached. Submitting data...");
        const timer = setInterval(() => setTimeLeft(prev => prev - 1), 1000);
        return () => clearInterval(timer);
    }, [timeLeft]);

    const toggleListening = (force = null) => {
        if (isAiSpeaking && force !== false) return; 
        const start = force !== null ? force : !isListening;
        
        try {
            if (start) {
                setUserInput('');
                recognitionRef.current?.start();
                setIsListening(true);
            } else {
                recognitionRef.current?.stop();
                setIsListening(false);
            }
        } catch (e) {
            console.warn("Recognition error handled:", e.message);
        }
    };

    const handleSend = async () => {
        if (!userInput.trim() || loading || isAiSpeaking) return;

        toggleListening(false);
        const answer = userInput;
        const currentQ = questions[currentIndex];
        
        setMessages(prev => [...prev, { role: 'user', text: answer }]);
        setLoading(true);

        try {
            // Get immediate feedback for the current answer
            const res = await axios.post("http://127.0.0.1:8000/api/interview/chat", {
                answer, question: currentQ, context
            });

            const feedback = res.data.reply;
            // Capture updated log in local variable for immediate use in Pivot logic
            const updatedLog = [...performanceLog, { question: currentQ, answer, feedback }];
            setPerformanceLog(updatedLog);
            setMessages(prev => [...prev, { role: 'ai', text: feedback, type: 'feedback' }]);
            
            speak(feedback, async () => {
                // --- A. THE PIVOT (8+5 Logic) ---
                if (currentIndex === 7 && phase === 'primary') {
                    setLoading(true);
                    try {
                        const pivotRes = await axios.post("http://127.0.0.1:8000/api/interview/pivot", {
                            history: updatedLog, // Sending the full 8-question history
                            context,
                            role
                        });
                        
                        const pivotQuestions = pivotRes.data.deep_dives;
                        const pivotIntro = `Neural Analysis: ${pivotRes.data.analysis}. Starting deep-dive phase.`;
                        
                        setMessages(prev => [...prev, { role: 'ai', text: pivotIntro }]);
                        setQuestions(pivotQuestions);
                        setCurrentIndex(0);
                        setPhase('deepdive');
                        setLoading(false);

                        speak(pivotIntro, () => {
                            askQuestion(0, pivotQuestions);
                        });
                    } catch (e) {
                        console.error("Pivot Trigger Failed:", e);
                        finishInterview("System Error: Critical failure in pivot module. Saving data.");
                    }
                } else {
                    // Normal Question Increment
                    const nextIdx = currentIndex + 1;
                    if (nextIdx < questions.length) {
                        setCurrentIndex(nextIdx);
                        askQuestion(nextIdx);
                    } else {
                        finishInterview();
                    }
                }
            });
        } catch (err) {
            console.error("Transmission Error:", err);
            alert("Neural Link Interrupted. Retrying...");
        } finally {
            setLoading(false);
        }
    };

    const finishInterview = (msg) => {
        const endMsg = msg || "Simulation complete. Transferring data to Intelligence Feed.";
        setMessages(prev => [...prev, { role: 'ai', text: endMsg }]);
        speak(endMsg, () => {
            // Pass the final report to dashboard
            navigate('/dashboard', { state: { report: performanceLog } });
        });
    };

    const formatTime = (s) => `${Math.floor(s/60)}:${(s%60).toString().padStart(2,'0')}`;

    return (
        <div className="h-screen bg-[#030303] text-slate-200 flex overflow-hidden font-sans selection:bg-blue-500/30">
            
            {/* LEFT SIDE (NEURAL HUD) */}
            <div className="flex-1 relative flex flex-col p-6 space-y-6">
                <div className="flex justify-between items-center z-10">
                    <div className="flex items-center gap-4">
                        <div className="p-2.5 bg-blue-600/20 rounded-xl border border-blue-500/30 shadow-[0_0_20px_rgba(37,99,235,0.2)]">
                            <Zap size={22} className="text-blue-400" fill="currentColor" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black tracking-[0.2em] text-blue-500 uppercase">Core Logic v2.5</p>
                            <p className="text-sm font-bold tracking-tight">
                                {phase === 'primary' ? 'PRIMARY EVALUATION' : 'DEEP-DIVE PHASE'}
                            </p>
                        </div>
                    </div>

                    <div className="flex gap-4">
                        <div className={`px-5 py-2.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 transition-colors ${timeLeft < 300 ? 'text-red-500 border-red-500/40 bg-red-500/5 animate-pulse' : 'border-white/10 bg-white/5'}`}>
                            <Clock size={18} />
                            <span className="font-mono text-lg font-black">{formatTime(timeLeft)}</span>
                        </div>
                        <div className="px-5 py-2.5 rounded-2xl bg-blue-600 text-white text-xs font-black shadow-[0_0_25px_rgba(37,99,235,0.4)] flex items-center">
                            {phase === 'primary' ? `NODE ${currentIndex + 1} / 8` : `PROBE ${currentIndex + 1} / 5`}
                        </div>
                    </div>
                </div>

                <div className="flex-1 relative group overflow-hidden rounded-[3rem] border border-white/10 bg-black shadow-inner">
                    <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover scale-x-[-1] opacity-70 contrast-125" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80" />
                    
                    {/* Recording Indicator */}
                    <div className="absolute top-8 left-8 flex items-center gap-2 bg-black/40 px-4 py-2 rounded-full border border-white/10 backdrop-blur-md">
                        <div className="w-2.5 h-2.5 bg-red-600 rounded-full animate-ping" />
                        <span className="text-[10px] font-black uppercase tracking-widest">Live Bio-Feed</span>
                    </div>

                    {/* Waveform visualizer */}
                    {isListening && (
                        <div className="absolute bottom-40 left-1/2 -translate-x-1/2 flex items-end gap-1.5 h-12">
                            {[1,2,3,4,5,6,7,8].map(i => (
                                <motion.div key={i} animate={{ height: [10, 40, 15, 35, 10] }} transition={{ repeat: Infinity, duration: 0.6, delay: i*0.08 }} className="w-1.5 bg-blue-500 rounded-full shadow-[0_0_15px_rgba(59,130,246,0.6)]" />
                            ))}
                        </div>
                    )}

                    {/* Active Question UI */}
                    <div className="absolute bottom-12 left-12 right-12">
                        <motion.div key={currentIndex + phase} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-white/[0.03] backdrop-blur-3xl border border-white/10 p-10 rounded-[2.5rem] shadow-2xl">
                            <div className="flex items-center gap-3 mb-4">
                                {isAiSpeaking ? <Volume2 size={20} className="text-blue-500 animate-bounce" /> : <Mic size={20} className="text-emerald-500" />}
                                <p className="text-[10px] font-black tracking-[0.4em] text-gray-500 uppercase">
                                    {isAiSpeaking ? 'Processing Speech...' : 'Awaiting Response...'}
                                </p>
                            </div>
                            <p className="text-3xl font-semibold leading-tight text-white italic tracking-tight">"{questions[currentIndex]}"</p>
                        </motion.div>
                    </div>
                </div>
            </div>

            {/* RIGHT SIDE (INTELLIGENCE FEED) */}
            <div className="w-[480px] bg-[#080809] border-l border-white/5 flex flex-col relative z-10">
                <div className="p-8 border-b border-white/5 flex items-center justify-between bg-black/40 backdrop-blur-md">
                    <div className="flex items-center gap-3">
                        <MessageSquare className="text-blue-500" size={20} />
                        <h3 className="font-bold text-sm tracking-widest uppercase">Intelligence Feed</h3>
                    </div>
                    <XCircle className="text-gray-600 hover:text-red-500 cursor-pointer transition-colors" onClick={() => navigate('/dashboard')} size={22} />
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-6 scrollbar-hide bg-[url('https://grainy-gradients.vercel.app/noise.svg')] bg-opacity-[0.02]">
                    <AnimatePresence initial={false}>
                        {messages.map((m, i) => (
                            <motion.div 
                                initial={{ opacity: 0, x: m.role === 'ai' ? -15 : 15 }} 
                                animate={{ opacity: 1, x: 0 }} 
                                key={i} 
                                className={`flex ${m.role === 'ai' ? 'justify-start' : 'justify-end'}`}
                            >
                                <div className={`max-w-[90%] p-6 rounded-[2rem] text-sm leading-relaxed ${
                                    m.role === 'ai' 
                                        ? m.type === 'feedback' 
                                            ? 'bg-gradient-to-br from-purple-500/10 to-blue-500/5 border border-purple-500/20 text-purple-100 shadow-[0_0_20px_rgba(168,85,247,0.05)]' 
                                            : 'bg-white/[0.03] border border-white/10 text-blue-50'
                                        : 'bg-blue-600 text-white font-medium shadow-xl'
                                }`}>
                                    <p className="text-[9px] font-black uppercase tracking-widest mb-1 opacity-40">
                                        {m.role === 'ai' ? 'Neural Response' : 'Candidate Output'}
                                    </p>
                                    {m.text}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                    {loading && (
                        <div className="flex gap-3 items-center text-blue-400 text-[10px] font-black tracking-widest uppercase animate-pulse p-4 bg-blue-500/5 border border-blue-500/10 rounded-2xl">
                            <Loader2 className="animate-spin" size={16} /> Analysis Engine Active...
                        </div>
                    )}
                    <div ref={chatEndRef} />
                </div>

                {/* Response Input Zone */}
                <div className="p-8 bg-black/60 border-t border-white/5 backdrop-blur-2xl">
                    <div className="relative group">
                        <div className={`absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-3xl blur opacity-20 transition duration-500 ${isListening ? 'opacity-40' : 'group-hover:opacity-30'}`} />
                        <div className="relative">
                            <textarea 
                                className={`w-full transition-all bg-[#0A0A0B] border border-white/10 rounded-[2rem] p-6 pr-20 text-sm outline-none resize-none h-32 scrollbar-hide ${isAiSpeaking ? 'opacity-30 grayscale cursor-not-allowed' : 'focus:border-blue-500/50'}`}
                                value={userInput}
                                onChange={e => setUserInput(e.target.value)}
                                placeholder={isAiSpeaking ? "Interviewer speaking..." : "Type or speak your answer..."}
                                disabled={isAiSpeaking || loading} 
                            />
                            <div className="absolute right-5 bottom-5 flex flex-col gap-3">
                                <button 
                                    onClick={() => toggleListening()} 
                                    disabled={isAiSpeaking || loading}
                                    title="Voice Input"
                                    className={`p-3.5 rounded-2xl transition-all shadow-lg ${isListening ? 'bg-red-500 animate-pulse text-white shadow-red-500/40' : 'bg-white/5 text-gray-400 hover:text-white hover:bg-white/10'}`}
                                >
                                    {isListening ? <Mic size={20} /> : <MicOff size={20} />}
                                </button>
                                <button 
                                    onClick={handleSend} 
                                    disabled={!userInput.trim() || loading || isAiSpeaking} 
                                    className="p-3.5 bg-blue-600 text-white rounded-2xl shadow-xl shadow-blue-600/30 disabled:opacity-20 transition-all hover:scale-105 active:scale-95"
                                >
                                    {loading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
                                </button>
                            </div>
                        </div>
                    </div>
                    <p className="text-[10px] text-center text-gray-600 font-bold tracking-[0.2em] uppercase mt-5">
                        {isListening ? "Listening... click mic to stop" : "Shift + Enter for New Line"}
                    </p>
                </div>
            </div>

            {/* Global Grainy Noise Overlays */}
            <div className="fixed inset-0 pointer-events-none opacity-[0.015] z-50">
                <div className="w-full h-full bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
            </div>
        </div>
    );
}