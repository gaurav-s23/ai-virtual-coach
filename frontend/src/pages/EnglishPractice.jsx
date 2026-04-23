import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
    BookOpen, MessageSquare, Award, Clock, Mic, MicOff, 
    Send, Zap, ChevronRight, BarChart3, Languages, Globe, 
    RefreshCcw, Loader2, Volume2, XCircle, ArrowLeft, Square, AlertTriangle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api, { startEnglishSession, sendEnglishMessage, eventSourceManager } from '../services/api';

// --- THEMED BACKGROUND (Deep Navy & Light Blue Glows) ---
const BackgroundEffect = () => (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none bg-[#010409]">
      <div className="absolute top-[-10%] left-[-10%] w-[70%] h-[70%] bg-cyan-600/10 blur-[140px] rounded-full animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-blue-500/10 blur-[140px] rounded-full animate-pulse delay-700" />
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]" />
    </div>
);

export default function EnglishPractice() {
    const navigate = useNavigate();
    
    // --- APP STATES ---
    const [step, setStep] = useState(1); // 1: Topic, 2: Timer, 3: Chat, 4: Report
    const [topic, setTopic] = useState("Synchronizing Topic...");
    const [questions, setQuestions] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [phase, setPhase] = useState('primary'); // 'primary' or 'deepdive'
    const [timer, setTimer] = useState(600); // 10 mins
    
    const [messages, setMessages] = useState([]);
    const [userInput, setUserInput] = useState("");
    const [isListening, setIsListening] = useState(false);
    const [isAiSpeaking, setIsAiSpeaking] = useState(false);
    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState(null);
    const [showEndDialog, setShowEndDialog] = useState(false);
    const [sessionId, setSessionId] = useState(null);
    const [sessionStarted, setSessionStarted] = useState(false);

    const recognitionRef = useRef(null);
    const chatEndRef = useRef(null);

    // --- Abandoned Session Tracking ---
    const markSessionAbandoned = async () => {
        if (sessionStarted && sessionId) {
            try {
                await api.post('/api/english/abandon-session', {
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

    // --- End Practice with Confirmation ---
    const handleEndPractice = () => {
        setShowEndDialog(true);
    };

    const confirmEndPractice = async () => {
        setShowEndDialog(false);
        if (sessionStarted && sessionId) {
            try {
                await api.post('/api/english/end-session', {
                    session_id: sessionId,
                    ended_at: new Date().toISOString(),
                    messages: messages,
                    status: 'completed'
                });
            } catch (error) {
                console.error('Failed to end session properly:', error);
            }
        }
        navigate('/dashboard');
    };

    const cancelEndPractice = () => {
        setShowEndDialog(false);
    };

    // --- 1. INITIALIZATION ---
    useEffect(() => {
        // Fetch Topic
        api.get('/api/english/topic')
            .then(res => setTopic(res.data.topic));

        // Setup Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = true;
            recognitionRef.current.interimResults = true;
            recognitionRef.current.onresult = (e) => {
                const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
                setUserInput(transcript);
            };
        }
    }, []);

    // --- 2. TIMER LOGIC (Briefing Phase) ---
    useEffect(() => {
        if (step === 2 && timer > 0) {
            const interval = setInterval(() => setTimer(prev => prev - 1), 1000);
            return () => clearInterval(interval);
        } else if (timer === 0 && step === 2) {
            initializeSimulation();
        }
    }, [step, timer]);

    const formatTime = (s) => `${Math.floor(s/60)}:${(s%60).toString().padStart(2, '0')}`;

    // --- 3. SPEECH & AI FLOW ---
    const speak = (text, callback) => {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.onstart = () => setIsAiSpeaking(true);
        utterance.onend = () => {
            setIsAiSpeaking(false);
            if (callback) callback();
        };
        window.speechSynthesis.speak(utterance);
    };

    const initializeSimulation = async () => {
        setLoading(true);
        try {
            const res = await api.post('/api/english/questions', { topic });
            setQuestions(res.data.questions);
            setStep(3);
            const newSessionId = res.data.session_id || `english_${Date.now()}`;
            setSessionId(newSessionId);
            setSessionStarted(true);
            
            // Mark session as started
            await api.post('/api/english/start-session', {
                session_id: newSessionId,
                topic: topic
            });
            
            const welcome = `Simulation initialized. Our topic is "${topic}". Let's begin. ${res.data.questions[0]}`;
            setMessages([{ role: 'ai', text: welcome }]);
            speak(welcome, () => toggleListening(true));
        } catch (e) {
            alert("Neural Link Failed.");
        } finally {
            setLoading(false);
        }
    };

    const toggleListening = (force = null) => {
        const start = force !== null ? force : !isListening;
        if (isAiSpeaking && start) return;
        try {
            if (start) {
                setUserInput("");
                recognitionRef.current?.start();
                setIsListening(true);
            } else {
                recognitionRef.current?.stop();
                setIsListening(false);
            }
        } catch (e) {}
    };

    const handleSend = async () => {
        if (!userInput.trim() || loading || isAiSpeaking) return;
        
        toggleListening(false);
        const answer = userInput;
        const currentMsgBatch = [...messages, { role: 'user', text: answer }];
        setMessages(currentMsgBatch);
        setLoading(true);
        setUserInput("");

        try {
            // After 5 primary questions, transition into deep-dive round.
            if (currentIndex === 4 && phase === 'primary') {
                // Generate deep-dive questions based on user's performance
                const deepDiveRes = await api.post('/api/english/questions', { 
                    topic, 
                    phase: 'deepdive',
                    history: currentMsgBatch 
                });
                
                setPhase('deepdive');
                setCurrentIndex(0);
                setQuestions(deepDiveRes.data.questions);
                const deepDiveIntro = "Primary round complete. Now entering deep-dive round with targeted follow-up questions.";
                setMessages(prev => [...prev, { role: 'ai', text: deepDiveIntro }, { role: 'ai', text: deepDiveRes.data.questions[0] }]);
                speak(`${deepDiveIntro} ${deepDiveRes.data.questions[0]}`, () => toggleListening(true));
            } 
            // If 5 deep-dives are done, generate report
            else if (currentIndex === 4 && phase === 'deepdive') {
                const res = await api.post('/api/english/report', { history: currentMsgBatch });
                setReport(res.data);
                setStep(4);
            } 
            // Normal sequential flow - use streaming for real-time feedback
            else {
                // Use streaming API for English practice feedback
                const streamUrl = sendEnglishMessage(sessionId, answer, true);
                
                // Create streaming connection for real-time feedback
                let accumulatedFeedback = '';
                
                const streamId = eventSourceManager.createEventSource(
                    `${api.API_BASE}${streamUrl}`,
                    (data, streamId) => {
                        if (data.type === 'content' && data.chunk) {
                            // Accumulate streaming feedback
                            accumulatedFeedback += data.chunk;
                            
                            // Update message with partial content
                            setMessages(prev => {
                                const updated = [...prev];
                                const lastMessage = updated[updated.length - 1];
                                if (lastMessage && lastMessage.type === 'streaming') {
                                    lastMessage.text = accumulatedFeedback;
                                } else {
                                    updated.push({ role: 'ai', text: accumulatedFeedback, type: 'streaming' });
                                }
                                return updated;
                            });
                        } else if (data.type === 'complete') {
                            // Streaming complete - finalize message and continue
                            const finalFeedback = data.feedback || accumulatedFeedback;
                            
                            // Finalize message
                            setMessages(prev => {
                                const updated = [...prev];
                                const lastMessage = updated[updated.length - 1];
                                if (lastMessage && lastMessage.type === 'streaming') {
                                    lastMessage.text = finalFeedback;
                                    lastMessage.type = 'feedback';
                                } else {
                                    updated.push({ role: 'ai', text: finalFeedback, type: 'feedback' });
                                }
                                return updated;
                            });
                            
                            // Continue with next question
                            const nextIdx = currentIndex + 1;
                            setCurrentIndex(nextIdx);
                            setMessages(prev => [...prev, { role: 'ai', text: questions[nextIdx] }]);
                            speak(questions[nextIdx], () => toggleListening(true));
                            setLoading(false);
                        } else if (data.type === 'error') {
                            console.error('Streaming error:', data.error);
                            setMessages(prev => [...prev, { role: 'ai', text: `Error: ${data.error}`, type: 'error' }]);
                            setLoading(false);
                        }
                    },
                    (error, streamId) => {
                        console.error('SSE error:', error);
                        setMessages(prev => [...prev, { role: 'ai', text: `Connection error: ${error.message || 'Unknown error'}`, type: 'error' }]);
                        setLoading(false);
                    }
                );
                
                return; // Exit early, streaming will handle the rest
            }
        } catch (e) {
            console.error(e);
            setLoading(false);
        }
    };

    // --- UI RENDERING ---

    return (
        <div className="min-h-screen bg-[#010409] text-slate-200 font-sans selection:bg-cyan-500/30 overflow-hidden relative">
            <BackgroundEffect />

            {/* STEP 1: TOPIC REVEAL */}
            {step === 1 && (
                <div className="relative z-10 h-screen flex items-center justify-center p-6">
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="max-w-2xl w-full bg-white/[0.03] border border-white/10 rounded-[3rem] p-12 text-center space-y-10 backdrop-blur-3xl shadow-2xl">
                        <div className="p-4 bg-cyan-500/10 w-fit mx-auto rounded-2xl border border-cyan-500/20 text-cyan-400">
                            <Globe size={40} className="animate-pulse" />
                        </div>
                        <div className="space-y-2">
                            <h2 className="text-4xl font-black italic uppercase tracking-tighter text-white">Oral Probe Assigned</h2>
                            <p className="text-gray-500 text-xs font-bold uppercase tracking-[0.4em]">Fluency Simulation Phase 01</p>
                        </div>
                        <div className="p-10 bg-black/40 border border-white/5 rounded-[2.5rem] text-3xl font-bold text-cyan-100 italic leading-tight">
                            "{topic}"
                        </div>
                        <button onClick={() => setStep(2)} className="w-full bg-cyan-600 hover:bg-cyan-500 text-white py-5 rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all shadow-[0_0_30px_rgba(6,182,212,0.3)]">
                            INITIALIZE BRIEFING
                        </button>
                    </motion.div>
                </div>
            )}

            {/* STEP 2: PREPARATION TIMER */}
            {step === 2 && (
                <div className="relative z-10 h-screen flex flex-col items-center justify-center p-6">
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center space-y-12">
                        <div className="space-y-2">
                            <p className="text-cyan-500 font-black uppercase tracking-[0.5em] text-xs">Research & Prep Window</p>
                            <h1 className="text-[12rem] font-black font-mono tracking-tighter text-white leading-none shadow-cyan-500/20 drop-shadow-2xl">
                                {formatTime(timer)}
                            </h1>
                        </div>
                        <div className="max-w-xl p-6 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-md">
                            <p className="text-gray-400 text-sm font-medium leading-relaxed italic">"Read about {topic}. Prepare points on global impacts and ethical considerations. The AI will begin the oral probe once the timer expires."</p>
                        </div>
                        <button onClick={initializeSimulation} className="px-12 py-4 bg-white text-black rounded-full font-black text-xs uppercase tracking-widest hover:bg-cyan-500 hover:text-white transition-all">
                            I AM READY • START PROBE
                        </button>
                    </motion.div>
                </div>
            )}

            {/* STEP 3: THE CHAT SIMULATION (5+5) */}
            {step === 3 && (
                <div className="relative z-10 h-screen flex max-w-[1400px] mx-auto overflow-hidden">
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
                                <div className="px-5 py-2.5 rounded-2xl bg-cyan-600 text-white text-xs font-black shadow-[0_0_25px_rgba(6,182,212,0.4)] flex items-center">
                                    {phase === 'primary' ? `INITIAL ${currentIndex + 1}/5` : `DEEP DIVE ${currentIndex + 1}/5`}
                                </div>
                                <button
                                    onClick={handleEndPractice}
                                    className="px-4 py-2.5 rounded-2xl bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 hover:text-red-300 transition-all flex items-center gap-2"
                                >
                                    <Square size={16} />
                                    <span className="text-xs font-black uppercase tracking-widest">End Practice</span>
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    {/* HUD SIDEBAR */}
                    <div className="w-96 p-10 border-r border-white/5 flex flex-col justify-between bg-black/20 backdrop-blur-md pt-20">
                        <div className="space-y-8">
                            <div className="flex items-center gap-3">
                                <div className="p-2.5 bg-cyan-600 rounded-xl shadow-[0_0_15px_rgba(6,182,212,0.4)]">
                                    <Languages size={20} className="text-white" />
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-cyan-500 uppercase tracking-widest leading-none mb-1">Active Probe</p>
                                    <h2 className="font-bold text-white uppercase tracking-tight text-sm">Fluency Coach</h2>
                                </div>
                            </div>
                            <div className="p-6 bg-white/[0.03] border border-white/10 rounded-[2rem]">
                                <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-3">Topic</p>
                                <p className="text-lg font-bold text-white italic leading-snug">"{topic}"</p>
                            </div>
                        </div>

                        {/* WAVEFORM VISUALIZER */}
                        <div className="space-y-6">
                            <div className="h-20 flex items-end justify-center gap-1.5 px-4">
                                {[1,2,3,4,5,6,7,8,9,10,11,12].map(i => (
                                    <motion.div 
                                        key={i}
                                        animate={{ height: isListening ? [10, Math.random() * 60 + 10, 10] : 10 }}
                                        transition={{ repeat: Infinity, duration: 0.5, delay: i * 0.05 }}
                                        className={`w-1.5 rounded-full ${isListening ? 'bg-cyan-500 shadow-[0_0_15px_cyan]' : 'bg-white/10'}`}
                                    />
                                ))}
                            </div>
                            <p className="text-center text-[10px] font-black text-gray-500 uppercase tracking-[0.4em]">
                                {isListening ? "Analyzing Neural Cadence" : "Mic Standby"}
                            </p>
                        </div>
                    </div>

                    {/* MAIN CHAT AREA */}
                    <div className="flex-1 flex flex-col bg-[#050505]/40 backdrop-blur-3xl">
                        <div className="flex-1 overflow-y-auto p-12 space-y-8 scrollbar-hide">
                            <AnimatePresence initial={false}>
                                {messages.map((m, i) => (
                                    <motion.div 
                                        key={i}
                                        initial={{ opacity: 0, x: m.role === 'ai' ? -20 : 20 }}
                                        animate={{ opacity: 1, x: 0 }}
                                        className={`flex ${m.role === 'ai' ? 'justify-start' : 'justify-end'}`}
                                    >
                                        <div className={`max-w-[80%] p-6 rounded-[2.5rem] text-sm leading-relaxed shadow-xl ${
                                            m.role === 'ai' 
                                            ? 'bg-white/[0.03] border border-white/10 text-cyan-50' 
                                            : 'bg-cyan-600 text-white font-medium border border-cyan-400/30'
                                        }`}>
                                            <p className="text-[9px] font-black uppercase tracking-widest mb-1 opacity-40">
                                                {m.role === 'ai' ? 'COACH_NODE' : 'USER_INPUT'}
                                            </p>
                                            {m.text}
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                            {loading && <div className="flex items-center gap-3 text-cyan-500 text-[10px] font-black animate-pulse"><Loader2 className="animate-spin" size={14}/> PROCESSING LINGUISTICS...</div>}
                            <div ref={chatEndRef} />
                        </div>

                        {/* RESPONSE HUB */}
                        <div className="p-10 border-t border-white/5 bg-black/40">
                            <div className="relative group max-w-4xl mx-auto">
                                <div className={`absolute -inset-0.5 bg-cyan-500 rounded-[2rem] blur opacity-10 transition duration-500 ${isListening ? 'opacity-30' : 'group-hover:opacity-20'}`} />
                                <div className="relative bg-[#0A0A0B] border border-white/10 rounded-[2rem] p-4 flex items-end gap-4 shadow-2xl">
                                    <textarea 
                                        value={userInput}
                                        onChange={(e) => setUserInput(e.target.value)}
                                        placeholder={isAiSpeaking ? "Coach is speaking..." : "Speak or type your response..."}
                                        disabled={isAiSpeaking}
                                        className="flex-1 bg-transparent p-4 outline-none resize-none text-sm h-14 scrollbar-hide focus:ring-0"
                                    />
                                    <div className="flex gap-2 mb-2 pr-2">
                                        <button 
                                            onClick={() => toggleListening()}
                                            disabled={isAiSpeaking}
                                            className={`p-4 rounded-xl transition-all ${isListening ? 'bg-red-500 text-white animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.4)]' : 'bg-white/5 text-gray-500 hover:text-cyan-400'}`}
                                        >
                                            {isListening ? <Mic size={20} /> : <MicOff size={20} />}
                                        </button>
                                        <button 
                                            onClick={handleSend}
                                            disabled={!userInput.trim() || loading || isAiSpeaking}
                                            className="p-4 bg-cyan-600 text-white rounded-xl shadow-xl hover:bg-cyan-500 disabled:opacity-20 active:scale-95 transition-all"
                                        >
                                            {loading ? <Loader2 className="animate-spin" size={20}/> : <Send size={20} />}
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <p className="text-center text-[10px] text-gray-600 font-bold uppercase tracking-[0.3em] mt-6">
                                PHASE: {phase === 'primary' ? 'INITIAL_EVAL' : 'DEEP_DIVE'} • PROGRESS: {currentIndex + 1}/5
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* STEP 4: FINAL REPORT */}
            {step === 4 && report && (
                <div className="relative z-10 min-h-screen flex items-center justify-center p-6">
                    <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl w-full bg-white/[0.03] border border-white/10 p-16 rounded-[4rem] backdrop-blur-3xl space-y-12 shadow-2xl">
                        <div className="text-center">
                            <div className="p-6 bg-cyan-500/20 w-fit mx-auto rounded-full mb-6 border border-cyan-500/20 shadow-[0_0_30px_rgba(6,182,212,0.2)]">
                                <Award size={56} className="text-cyan-400" />
                            </div>
                            <h2 className="text-5xl font-black italic uppercase tracking-tighter text-white leading-none">Fluency Dossier</h2>
                            <p className="text-cyan-500 font-bold tracking-[0.4em] uppercase text-[11px] mt-6">Candidate Proficiency: {report.overall_score} / 100</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                            <ScoreCard label="Technical Rating" value={report.technical_rating} color="cyan" />
                            <ScoreCard label="Communication" value={report.communication_rating} color="blue" />
                            <ScoreCard label="Overall Score" value={report.overall_score} color="indigo" />
                        </div>

                        <div className="p-10 bg-black/40 border border-white/10 rounded-[3rem] italic text-gray-200 text-lg text-center leading-relaxed font-medium">
                            <p className="text-[10px] not-italic font-black text-cyan-500 uppercase tracking-widest mb-4">Neural Critique</p>
                            "{report.brutal_feedback}"
                        </div>

                        <div className="flex gap-4">
                            <button onClick={() => window.location.reload()} className="flex-1 bg-white/5 border border-white/10 text-white py-6 rounded-3xl font-black uppercase text-xs tracking-widest hover:bg-white/10 transition-all">Restart Simulation</button>
                            <button onClick={() => navigate('/dashboard')} className="flex-1 bg-cyan-600 text-white py-6 rounded-3xl font-black uppercase text-xs tracking-widest hover:bg-cyan-500 transition-all shadow-2xl shadow-cyan-600/20">Return to Hub</button>
                        </div>
                    </motion.div>
                </div>
            )}

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
                                <h3 className="text-2xl font-bold text-white">End Practice?</h3>
                            </div>
                            <p className="text-gray-300 mb-8 leading-relaxed">
                                Are you sure you want to end the practice session? Your progress will be saved and you won't be able to continue.
                            </p>
                            <div className="flex gap-4">
                                <button
                                    onClick={cancelEndPractice}
                                    className="flex-1 px-6 py-3 bg-gray-600/20 hover:bg-gray-600/30 border border-gray-500/30 text-gray-400 hover:text-gray-300 rounded-2xl font-bold transition-all"
                                >
                                    No, Continue
                                </button>
                                <button
                                    onClick={confirmEndPractice}
                                    className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold transition-all"
                                >
                                    Yes, End Practice
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

const ScoreCard = ({ label, value, color }) => (
    <div className="bg-white/[0.02] border border-white/5 p-10 rounded-[3rem] text-center group hover:border-cyan-500/30 transition-all">
        <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest mb-3">{label}</p>
        <p className={`text-6xl font-black text-white group-hover:text-cyan-400 transition-colors`}>{value}%</p>
    </div>
);