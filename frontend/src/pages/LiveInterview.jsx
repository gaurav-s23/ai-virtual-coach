import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Mic, Send, Loader2, MicOff, MessageSquare, XCircle, Zap, Volume2, Clock, ArrowLeft, Square, AlertTriangle } from 'lucide-react';
import api, { startInterview, sendInterviewMessage, eventSourceManager } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';

export default function LiveInterview() {
    const location = useLocation();
    const navigate = useNavigate();

    // --- STATE FROM ROUTE ---
    const { 
        session_id = null,
        skill_questions = [],
        project_questions = [],
        jd_text = "",
        resume_text = "",
        role = "Software Engineer",
        candidate_name = "Candidate",
        interview_status = "starting",
        countdown_seconds = 8,
        duration = "30 mins",
    } = location.state || {};

    const [sessionRecovered, setSessionRecovered] = useState(false);
    const [sessionLoading, setSessionLoading] = useState(false);
    const [sessionError, setSessionError] = useState(null);
    const [showEndDialog, setShowEndDialog] = useState(false);
    const [sessionStarted, setSessionStarted] = useState(false);

    const hasValidSession = !!session_id && !!skill_questions?.length;

    // --- Abandoned Session Tracking ---
    const markSessionAbandoned = async () => {
        if (sessionStarted && session_id) {
            try {
                await api.post('/api/interview/abandon-session', {
                    session_id: session_id,
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
    }, [sessionStarted, session_id]);

    // --- End Interview with Confirmation ---
    const handleEndInterview = () => {
        setShowEndDialog(true);
    };

    const confirmEndInterview = async () => {
        setShowEndDialog(false);
        if (sessionStarted && session_id) {
            try {
                await api.post('/api/interview/end-session', {
                    session_id: session_id,
                    ended_at: new Date().toISOString(),
                    performance_log: performanceLog,
                    status: 'completed'
                });
            } catch (error) {
                console.error('Failed to end session properly:', error);
            }
        }
        finishInterview("Interview ended by user");
    };

    const cancelEndInterview = () => {
        setShowEndDialog(false);
    };

    const [questions, setQuestions] = useState([]);
    const [skillQuestions, setSkillQuestions] = useState([]);
    const [projectQuestions, setProjectQuestions] = useState([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [messages, setMessages] = useState([{ role: 'ai', text: intro }]);
    const [userInput, setUserInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isListening, setIsListening] = useState(false);
    const [isAiSpeaking, setIsAiSpeaking] = useState(false); 
    const [phase, setPhase] = useState('skills');
    const [timeLeft, setTimeLeft] = useState(initialTimeLeft); 
    const [startCountdown, setStartCountdown] = useState(countdown_seconds);
    const [statusText, setStatusText] = useState("Preparing interview...");
    const [performanceLog, setPerformanceLog] = useState([]);
    const [confidenceScore, setConfidenceScore] = useState(75);
    const [visionData, setVisionData] = useState({
        is_looking_at_camera: true,
        confidence_score: 75,
        face_detected: true,
        engagement_level: "high"
    });

    const videoRef = useRef(null);
    const chatEndRef = useRef(null);
    const recognitionRef = useRef(null);
    const wsRef = useRef(null);
    const questionStartTime = useRef(Date.now());
    const visionIntervalRef = useRef(null);

    const activeQuestion = questions[currentIndex] || "Preparing your first question...";

    // Convert duration string to seconds
    const getDurationInSeconds = (durationStr) => {
        const match = durationStr.match(/(\d+)\s*mins?/);
        return match ? parseInt(match[1]) * 60 : 1800; // Default to 30 mins
    };

    const initialTimeLeft = getDurationInSeconds(duration);

    const logProctorEvent = async (event_type) => {
        try { await api.post('/api/proctor/log', { session_id, event_type, timestamp: new Date().toISOString() }); }
        catch {}
    };

    const recoverSession = async () => {
        setSessionLoading(true);
        setSessionError(null);
        try {
            const token = localStorage.getItem('token');
            const response = await api.get('/api/interview/recover-session', {
                headers: { Authorization: `Bearer ${token}` }
            });
            
            if (response.data && response.data.session_id) {
                const recoveredSession = response.data;
                setSessionRecovered(true);
                // Update component state with recovered session data
                window.location.href = `/live-interview?session=${recoveredSession.session_id}`;
            } else {
                setSessionError('No active session found');
            }
        } catch (error) {
            console.error('Session recovery failed:', error);
            setSessionError('Failed to recover session. Please start a new interview.');
        } finally {
            setSessionLoading(false);
        }
    };

    // D. AUTO-SCROLL LOGIC
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    useEffect(() => {
        const onBlur = () => logProctorEvent('tab_switch');
        const onHide = () => { if (document.hidden) logProctorEvent('tab_hidden'); };
        window.addEventListener('blur', onBlur);
        document.addEventListener('visibilitychange', onHide);
        return () => {
            window.removeEventListener('blur', onBlur);
            document.removeEventListener('visibilitychange', onHide);
        };
    }, [session_id]);

    useEffect(() => {
        if (!session_id) return;
        const wsBase = (import.meta?.env?.VITE_API_URL || 'http://localhost:8000').replace('http', 'ws');
        const token = localStorage.getItem('token');
        const wsUrl = `${wsBase}/ws/interview/${session_id}?token=${encodeURIComponent(token || '')}`;
        wsRef.current = new WebSocket(wsUrl);
        wsRef.current.onmessage = (evt) => {
            try {
                const fb = JSON.parse(evt.data);
                if (fb.tip) setMessages(prev => [...prev, { role: 'ai', text: fb.tip, type: 'realtime' }]);
            } catch {}
        };
        wsRef.current.onerror = () => {};
        return () => wsRef.current?.close();
    }, [session_id]);

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
        questionStartTime.current = Date.now();

        setMessages(prev => [...prev, { role: 'ai', text: q }]);
        speak(q, () => {
            toggleListening(true);
        });
    };

    // INTERVIEW LIFECYCLE
    useEffect(() => {
        if (!hasValidSession) return;
        
        setSessionStarted(true);
        
        // Camera setup
        navigator.mediaDevices.getUserMedia({ video: true, audio: true })
            .then(stream => { if (videoRef.current) videoRef.current.srcObject = stream; })
            .catch(err => console.error("Camera Blocked:", err));

        // STT setup
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            setStatusText("Voice input not supported. Please use text input.");
            return;
        }
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.onresult = (e) => {
            const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
            setUserInput(transcript);
        };
        recognitionRef.current.onend = () => setIsListening(false);

        // Start Sequence
        const initialSkillQuestions = skill_questions || [];
        const initialProjectQuestions = project_questions || [];
        setSkillQuestions(initialSkillQuestions);
        setProjectQuestions(initialProjectQuestions);
        setQuestions(initialSkillQuestions);
        setPhase('skills');
        speak(intro, () => {
            setStatusText("Starting...");
            const interval = setInterval(() => {
                setStartCountdown((prev) => {
                    if (prev <= 1) {
                        clearInterval(interval);
                        setStatusText("Question 1...");
                        if (initialSkillQuestions.length > 0) askQuestion(0, initialSkillQuestions);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        });

        return () => {
            window.speechSynthesis.cancel();
            if (recognitionRef.current) recognitionRef.current.stop();
        };
    }, [intro, project_questions, skill_questions, followup_questions]);

    // Timer Logic
    useEffect(() => {
        if (timeLeft <= 0) return finishInterview("Simulation Time Limit Reached. Submitting data...");
        const timer = setInterval(() => setTimeLeft(prev => prev - 1), 1000);
        return () => clearInterval(timer);
    }, [timeLeft]);

    // Vision and Confidence Monitoring
    useEffect(() => {
        if (!hasValidSession) return;

        // Real camera capture and vision analysis
        visionIntervalRef.current = setInterval(async () => {
            try {
                if (videoRef.current && videoRef.current.readyState === 4) {
                    // Create canvas to capture frame
                    const canvas = document.createElement('canvas');
                    canvas.width = videoRef.current.videoWidth;
                    canvas.height = videoRef.current.videoHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
                    
                    // Convert to base64
                    const frameData = canvas.toDataURL('image/jpeg', 0.8);
                    
                    // Send to vision analysis API
                    const token = localStorage.getItem('token');
                    const response = await fetch('/api/vision/analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify({
                            frame_data: frameData,
                            session_id: session_id
                        })
                    });
                    
                    if (response.ok) {
                        const visionData = await response.json();
                        setVisionData({
                            is_looking_at_camera: visionData.is_looking_at_camera,
                            confidence_score: visionData.confidence_score,
                            face_detected: visionData.face_detected,
                            engagement_level: visionData.engagement_level
                        });
                    }
                }
            } catch (error) {
                console.warn('Vision analysis failed:', error);
                // Vision analysis unavailable - will retry on next interval
            }
        }, 4000); // Update every 4 seconds

        return () => {
            if (visionIntervalRef.current) {
                clearInterval(visionIntervalRef.current);
            }
        };
    }, [hasValidSession, session_id]);

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
        const timeTaken = (Date.now() - questionStartTime.current) / 1000;
        const isUserAsking = answer.trim().endsWith('?') && answer.trim().split(' ').length < 12;

        if (isUserAsking) {
            const redirect = "That's a fair thought, but let's stay focused on the interview. " + questions[currentIndex];
            setMessages(prev => [...prev, { role: 'ai', text: redirect }]);
            speak(redirect, () => toggleListening(true));
            setLoading(false);
            setUserInput('');
            return;
        }

        setMessages(prev => [...prev, { role: 'user', text: answer }]);
        setLoading(true);
        setUserInput('');

        try {
            // Use streaming API for interview feedback
            const streamUrl = sendInterviewMessage(session_id, answer, true);
            
            // Create streaming connection for real-time feedback
            let accumulatedFeedback = '';
            let confidenceScore = null;
            
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
                        // Streaming complete - finalize message
                        const finalFeedback = data.feedback || accumulatedFeedback;
                        
                        // Update confidence score from backend analysis
                        if (data.confidence_score) {
                            setConfidenceScore(data.confidence_score);
                            confidenceScore = data.confidence_score;
                        }
                        
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
                        
                        // Continue with TTS and next question logic
                        continueInterviewFlow(finalFeedback, confidenceScore);
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
            
            return; // Exit early, continueInterviewFlow will handle the rest

        } catch (err) {
            console.error("Transmission Error:", err);
            if (err?.response?.status === 404) {
                alert("Session expired");
            } else if (err?.response?.status === 503) {
                alert("Timeout retry");
            } else {
                alert("Server error, try again");
            }
        } finally {
            setLoading(false);
        }
    };

// Helper function to continue interview flow after streaming
const continueInterviewFlow = async (feedback, confidenceScore) => {
    const currentQ = questions[currentIndex];
    const updatedLog = [...performanceLog, { question: currentQ, answer, feedback, confidence_score: confidenceScore }];
    setPerformanceLog(updatedLog);
    
    speak(feedback, async () => {
        if (phase === 'skills' && currentIndex >= skillQuestions.length - 1) {
            setQuestions(projectQuestions);
            setCurrentIndex(0);
            setPhase('projects');
            setStatusText("Project round started");
            const msg = "Good. Now let's talk about your projects.";
            setMessages(prev => [...prev, { role: 'ai', text: msg }]);
            speak(msg, () => askQuestion(0, projectQuestions));
        } else if (phase === 'projects' && currentIndex >= projectQuestions.length - 1) {
            setLoading(true);
            try {
                const pivotRes = await api.post('/api/interview/pivot', {
                    history: updatedLog,
                    context,
                    role,
                    session_id
                });
                
                const followups = pivotRes.data.deep_dives || [];
                const pivotIntro = `Analysis complete. ${pivotRes.data.analysis} Let me ask some deeper questions.`;
                
                setMessages(prev => [...prev, { role: 'ai', text: pivotIntro }]);
                setQuestions(followups);
                setCurrentIndex(0);
                setPhase('followup');
                setStatusText("Follow-up round started");
                setLoading(false);

                speak(pivotIntro, () => {
                    askQuestion(0, followups);
                });
            } catch (e) {
                console.error("Pivot Trigger Failed:", e);
                finishInterview("System Error: Critical failure in pivot module. Saving data.");
            }
        } else if (phase === 'followup' && currentIndex >= questions.length - 1) {
            finishInterview();
        } else {
            const nextIdx = currentIndex + 1;
            setCurrentIndex(nextIdx);
            setStatusText(`Question ${nextIdx + 1}...`);
            askQuestion(nextIdx);
        }
    });
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

    if (!hasValidSession) {
        return (
            <div className="h-screen bg-slate-900 text-slate-200 flex items-center justify-center font-sans p-6">
                <div className="w-full max-w-xl p-10 rounded-3xl border border-white/10 bg-white/[0.03] text-center space-y-6">
                    <h2 className="text-3xl font-black text-white">Session Expired</h2>
                    <p className="text-slate-400">
                        {sessionError || "Session not found or expired. Would you like to try recovering your last active session?"}
                    </p>
                    
                    {sessionLoading ? (
                        <div className="flex items-center justify-center gap-2">
                            <Loader2 className="animate-spin" size={20} />
                            <span>Recovering session...</span>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            <button
                                onClick={recoverSession}
                                className="w-full px-6 py-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-bold transition-colors"
                            >
                                Recover Last Session
                            </button>
                            <button
                                onClick={() => navigate('/setup-interview')}
                                className="w-full px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-bold transition-colors"
                            >
                                Start New Interview
                            </button>
                        </div>
                    )}
                    
                    {sessionError && (
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="w-full px-6 py-2 text-slate-400 hover:text-white text-sm transition-colors"
                        >
                            Return to Dashboard
                        </button>
                    )}
                </div>
            </div>
        );
    }

    if (questions.length === 0) {
        return (
            <div className="h-screen bg-[#030303] text-slate-200 flex items-center justify-center font-sans">
                <div className="w-full max-w-2xl p-10 rounded-3xl border border-white/10 bg-white/[0.03] space-y-4">
                    <div className="h-5 w-4/5 rounded bg-white/10 animate-pulse" />
                    <div className="h-5 w-3/5 rounded bg-white/10 animate-pulse" />
                    <div className="h-5 w-2/3 rounded bg-white/10 animate-pulse" />
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen bg-[#030303] text-slate-200 flex overflow-hidden font-sans selection:bg-blue-500/30 relative">
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
                        <div className="px-5 py-2.5 rounded-2xl bg-blue-600 text-white text-xs font-black shadow-[0_0_25px_rgba(37,99,235,0.4)] flex items-center">
                            {phase === 'skills'
                                ? `SKILL ${currentIndex + 1} / ${skillQuestions.length || 5}`
                                : phase === 'projects'
                                    ? `PROJECT ${currentIndex + 1} / ${projectQuestions.length || 5}`
                                    : `FOLLOWUP ${currentIndex + 1} / ${questions.length || 5}`
                            }
                        </div>
                        <button
                            onClick={handleEndInterview}
                            className="px-4 py-2.5 rounded-2xl bg-red-600/20 hover:bg-red-600/30 border border-red-500/30 text-red-400 hover:text-red-300 transition-all flex items-center gap-2"
                        >
                            <Square size={16} />
                            <span className="text-xs font-black uppercase tracking-widest">End Interview</span>
                        </button>
                    </div>
                </div>
            </div>
            
            {/* LEFT SIDE (NEURAL HUD) */}
            <div className="flex-1 relative flex flex-col p-6 space-y-6 pt-20">
                <div className="flex justify-between items-center z-10">
                    <div className="flex items-center gap-4">
                        <div className="p-2.5 bg-blue-600/20 rounded-xl border border-blue-500/30 shadow-[0_0_20px_rgba(37,99,235,0.2)]">
                            <Zap size={22} className="text-blue-400" fill="currentColor" />
                        </div>
                        <div>
                            <p className="text-[10px] font-black tracking-[0.2em] text-blue-500 uppercase">Core Logic v2.5</p>
                            <p className="text-[10px] font-black tracking-[0.2em] text-emerald-400 uppercase">Candidate: {candidate_name}</p>
                            <p className="text-sm font-bold tracking-tight">
                                {phase === 'skills' ? 'SKILLS PHASE' : phase === 'projects' ? 'PROJECTS PHASE' : 'FOLLOW-UP PHASE'}
                            </p>
                            <p className="text-xs text-slate-400">{statusText} {startCountdown > 0 ? `(${startCountdown}s)` : ""}</p>
                        </div>
                    </div>

                    <div className="flex gap-4">
                        <div className={`px-5 py-2.5 rounded-2xl border backdrop-blur-xl flex items-center gap-3 transition-colors ${timeLeft < 300 ? 'text-red-500 border-red-500/40 bg-red-500/5 animate-pulse' : 'border-white/10 bg-white/5'}`}>
                            <Clock size={18} />
                            <span className="font-mono text-lg font-black">{formatTime(timeLeft)}</span>
                        </div>
                        <div className="px-5 py-2.5 rounded-2xl bg-blue-600 text-white text-xs font-black shadow-[0_0_25px_rgba(37,99,235,0.4)] flex items-center">
                            {phase === 'skills'
                                ? `SKILL ${currentIndex + 1} / ${skillQuestions.length || 5}`
                                : phase === 'projects'
                                    ? `PROJECT ${currentIndex + 1} / ${projectQuestions.length || 5}`
                                    : `FOLLOWUP ${currentIndex + 1} / ${questions.length || 5}`
                            }
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

                    {/* Vision Overlay */}
                    <div className="absolute top-8 right-8 flex flex-col gap-3">
                        {/* Eye Contact Indicator */}
                        <div className={`flex items-center gap-2 px-3 py-2 rounded-full backdrop-blur-md border transition-all ${
                            visionData.is_looking_at_camera 
                                ? 'bg-emerald-500/20 border-emerald-500/40' 
                                : 'bg-orange-500/20 border-orange-500/40'
                        }`}>
                            <div className={`w-2 h-2 rounded-full ${
                                visionData.is_looking_at_camera ? 'bg-emerald-500' : 'bg-orange-500'
                            } ${visionData.is_looking_at_camera ? 'animate-pulse' : ''}`} />
                            <span className="text-[10px] font-black uppercase tracking-widest">
                                {visionData.is_looking_at_camera ? 'Eye Contact' : 'Look at Camera'}
                            </span>
                        </div>

                        {/* Engagement Level */}
                        <div className={`px-3 py-2 rounded-full backdrop-blur-md border text-[10px] font-black uppercase tracking-widest ${
                            visionData.engagement_level === 'high' 
                                ? 'bg-blue-500/20 border-blue-500/40 text-blue-400'
                                : visionData.engagement_level === 'medium'
                                    ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400'
                                    : 'bg-red-500/20 border-red-500/40 text-red-400'
                        }`}>
                            {visionData.engagement_level.toUpperCase()} ENGAGEMENT
                        </div>
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
                            <p className="text-3xl font-semibold leading-tight text-white italic tracking-tight">"{activeQuestion}"</p>
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
                                            : m.type === 'realtime'
                                                ? 'bg-gradient-to-br from-emerald-500/10 to-cyan-500/5 border border-emerald-500/20 text-emerald-100 shadow-[0_0_20px_rgba(16,185,129,0.05)]'
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
                                <h3 className="text-2xl font-bold text-white">End Interview?</h3>
                            </div>
                            <p className="text-gray-300 mb-8 leading-relaxed">
                                Are you sure you want to end the interview? Your session will be concluded and you won't be able to continue.
                            </p>
                            <div className="flex gap-4">
                                <button
                                    onClick={cancelEndInterview}
                                    className="flex-1 px-6 py-3 bg-gray-600/20 hover:bg-gray-600/30 border border-gray-500/30 text-gray-400 hover:text-gray-300 rounded-2xl font-bold transition-all"
                                >
                                    No, Continue
                                </button>
                                <button
                                    onClick={confirmEndInterview}
                                    className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-2xl font-bold transition-all"
                                >
                                    Yes, End Interview
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Global Grainy Noise Overlays */}
            <div className="fixed inset-0 pointer-events-none opacity-[0.015] z-50">
                <div className="w-full h-full bg-[url('https://grainy-gradients.vercel.app/noise.svg')]" />
            </div>
        </div>
    );
}