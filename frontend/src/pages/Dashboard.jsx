import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
    Zap, Mic, BookOpen, Layout, LogOut,
    Flame, Target, Activity,
    Cpu, Trophy, CalendarCheck, Gauge
} from 'lucide-react';
import api from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorState from '../components/ErrorState';
import StatCard from '../components/StatCard';
import SkillBars from '../components/SkillBars';

export default function Dashboard() {
    const navigate = useNavigate();
    const location = useLocation();
    
    const defaultStats = {
        readiness: 65,
        attendance: 1,
        interviews: 0,
        mocks: 0,
        avgScore: 0,
        lastScore: 0,
        skills: [
            { subject: 'Technical', A: 60 },
            { subject: 'Logic', A: 50 },
            { subject: 'Confidence', A: 70 },
            { subject: 'Communication', A: 55 },
            { subject: 'Pace', A: 60 },
        ],
        email: null,
    };

    // --- PERSISTENT LOGIC: Load data from LocalStorage ---
    const [stats, setStats] = useState(() => {
        const saved = localStorage.getItem('neural_stats');
        return saved ? JSON.parse(saved) : defaultStats;
    });

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const getUserId = () => {
        try {
            const user = JSON.parse(localStorage.getItem('user'));
            return user?.id ?? 1;
        } catch {
            return 1;
        }
    };

    const fetchDashboard = async () => {
        const userId = getUserId();
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/api/dashboard', {
                params: { user_id: userId },
                timeout: 8000,
            });
            const data = res.data;
            const merged = { ...defaultStats, ...data };
            setStats(merged);
            localStorage.setItem('neural_stats', JSON.stringify(merged));
        } catch {
            setError('Backend unreachable. Please check your connection and try again.');
        } finally {
            setLoading(false);
        }
    };

    // --- FETCH ON MOUNT ---
    useEffect(() => {
        fetchDashboard();
    }, []);

    // --- UPDATE LOGIC: If user just came from an attempt ---
    useEffect(() => {
        if (location.state?.report) {
            const report = location.state.report;
            // Simple calculation: Accuracy based on feedback length/quality (Simulated)
            const newScore = Math.min(100, 70 + (report.length * 2)); 
            
            const updatedStats = {
                ...stats,
                interviews: stats.interviews + 1,
                lastScore: newScore,
                avgScore: stats.avgScore === 0 ? newScore : Math.round((stats.avgScore + newScore) / 2),
                readiness: Math.min(100, stats.readiness + 2),
                // Update technical skill area based on attempt
                skills: stats.skills.map(s => s.subject === 'Technical' ? { ...s, A: Math.min(100, s.A + 5) } : s)
            };
            setStats(updatedStats);
            localStorage.setItem('neural_stats', JSON.stringify(updatedStats));
            // Clear location state to prevent double counting
            window.history.replaceState({}, document.title);
        }

        if (location.state?.mockResult) {
            const updatedStats = {
                ...stats,
                mocks: stats.mocks + 1,
                readiness: Math.min(100, stats.readiness + 1),
                skills: stats.skills.map(s => s.subject === 'Logic' ? { ...s, A: Math.min(100, s.A + 3) } : s)
            };
            setStats(updatedStats);
            localStorage.setItem('neural_stats', JSON.stringify(updatedStats));
            window.history.replaceState({}, document.title);
        }
    }, []);

    return (
        <div className="flex h-screen bg-[#020617] text-slate-200 font-sans overflow-hidden relative">
            
            {/* --- BACKGROUND --- */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-cyan-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(6,182,212,0.10),transparent_45%),radial-gradient(circle_at_80%_30%,rgba(59,130,246,0.10),transparent_45%),radial-gradient(circle_at_50%_80%,rgba(139,92,246,0.10),transparent_50%)] pointer-events-none" />
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-[0.025] pointer-events-none" />
            </div>

            {/* --- SIDEBAR --- */}
            <aside className="w-72 border-r border-white/5 flex flex-col p-8 space-y-10 bg-black/20 backdrop-blur-3xl z-20">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-xl shadow-[0_0_20px_rgba(6,182,212,0.3)]">
                        <Zap size={22} className="text-white" fill="white" />
                    </div>
                    <span className="font-black tracking-tighter text-2xl text-white uppercase italic">Neural<span className="text-cyan-400">AI</span></span>
                </div>
                
                <nav className="flex-1 space-y-2">
                    <NavItem icon={<Layout size={18}/>} label="Command Deck" active />
                    <NavItem icon={<Activity size={18}/>} label="Neural Feed" />
                    <NavItem icon={<CalendarCheck size={18}/>} label="Attendance" />
                    <NavItem icon={<Trophy size={18}/>} label="Achievements" />
                </nav>

                <button onClick={() => navigate('/')} className="flex items-center gap-3 p-4 text-red-400/70 hover:text-red-400 hover:bg-red-500/5 rounded-2xl transition-all font-bold text-xs uppercase tracking-widest">
                    <LogOut size={16}/> <span>Terminate</span>
                </button>
            </aside>

            {/* --- MAIN CONTENT --- */}
            <main className="flex-1 overflow-y-auto relative z-10 p-12 custom-scrollbar">
                <div className="max-w-6xl mx-auto space-y-10">
                    
                    {/* TOP HEADER */}
                    <header className="flex justify-between items-end">
                        <div>
                            <p className="text-cyan-500 font-mono text-[10px] uppercase tracking-[0.4em] mb-2 font-black">System Ready: {userEmail()}</p>
                            <h1 className="text-5xl font-black text-white tracking-tighter">Command Centre</h1>
                        </div>
                        <div className="flex gap-4">
                            <StatPill icon={<Flame size={18}/>} label="STREAK" value={`${stats.attendance} DAYS`} color="orange" />
                            <StatPill icon={<Trophy size={18}/>} label="TOTAL ATTEMPTS" value={stats.interviews + stats.mocks} color="cyan" />
                        </div>
                    </header>

                    {/* STATUS STRIP */}
                    {loading ? (
                        <LoadingSpinner label="Syncing dashboard" />
                    ) : error ? (
                        <ErrorState message={error} onRetry={fetchDashboard} />
                    ) : null}

                    {/* PROGRESS TO TARGET BAR */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex justify-between items-center mb-4">
                            <div className="flex items-center gap-3">
                                <Target className="text-cyan-400" />
                                <span className="font-black text-xs uppercase tracking-widest">Path to Senior Architect</span>
                            </div>
                            <span className="font-mono text-cyan-400 text-sm font-black">{stats.readiness}%</span>
                        </div>
                        <div className="w-full h-3 bg-black/40 rounded-full overflow-hidden border border-white/5 p-0.5">
                            <motion.div 
                                initial={{ width: 0 }} 
                                animate={{ width: `${stats.readiness}%` }}
                                className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full shadow-[0_0_15px_rgba(6,182,212,0.5)]" 
                            />
                        </div>
                    </div>

                    {/* --- THE ANALYTICS GRID --- */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                        <div className="space-y-6">
                            <StatCard
                                icon={<Gauge size={18} />}
                                label="Readiness"
                                value={`${stats.readiness}%`}
                                hint="Signal strength for senior-track readiness."
                                tone="cyan"
                            />
                            <StatCard
                                icon={<Mic size={18} />}
                                label="Interviews"
                                value={stats.interviews}
                                hint="Brutal probes completed."
                                tone="blue"
                            />
                            <StatCard
                                icon={<BookOpen size={18} />}
                                label="Mocks"
                                value={stats.mocks}
                                hint="Assessments attempted."
                                tone="violet"
                            />
                        </div>

                        <div className="lg:col-span-2">
                            <SkillBars skills={stats.skills} />
                            <div className="mt-6 bg-gradient-to-br from-cyan-600/90 to-blue-700/90 p-8 rounded-[2.5rem] shadow-xl relative overflow-hidden group border border-white/10">
                                <Cpu className="absolute -right-4 -bottom-4 w-32 h-32 text-white/10 group-hover:scale-110 transition-transform" />
                                <p className="text-[10px] font-black text-cyan-100 uppercase tracking-widest mb-2">Next Milestone</p>
                                <h4 className="text-2xl font-black text-white italic">Technical Principal</h4>
                                <p className="text-cyan-100/70 text-xs mt-4 leading-relaxed font-medium">
                                    Complete 5 more high-score interviews to unlock advanced system design probes.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

// --- SUB-COMPONENTS ---

const NavItem = ({ icon, label, active = false }) => (
    <div className={`flex items-center gap-4 p-4 rounded-2xl transition-all cursor-pointer group ${active ? 'bg-cyan-500/10 text-white border border-cyan-500/20' : 'text-slate-500 hover:bg-white/5'}`}>
        <div className={`${active ? 'text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.4)]' : 'group-hover:text-cyan-400'} transition-colors`}>{icon}</div>
        <span className="text-sm font-black uppercase tracking-widest">{label}</span>
    </div>
);

const StatPill = ({ icon, label, value, color }) => (
    <div className={`bg-${color}-500/10 border border-${color}-500/20 px-6 py-4 rounded-[2rem] flex items-center gap-4`}>
        <div className={`text-${color}-500`}>{icon}</div>
        <div>
            <p className={`text-[9px] font-black text-${color}-500/60 uppercase tracking-widest leading-none`}>{label}</p>
            <p className="text-xl font-black font-mono leading-none mt-1.5 text-white">{value}</p>
        </div>
    </div>
);

const AttemptCard = ({ icon, label, count, color }) => (
    <div className="bg-white/[0.02] border border-white/5 p-8 rounded-[2.5rem] flex items-center justify-between group hover:border-cyan-500/30 transition-all">
        <div className="flex items-center gap-5">
            <div className={`p-4 rounded-2xl bg-${color}-500/10 text-${color}-400 group-hover:scale-110 transition-transform`}>{icon}</div>
            <p className="text-xs font-black text-slate-400 uppercase tracking-widest">{label}</p>
        </div>
        <span className="text-3xl font-black text-white italic">{count}</span>
    </div>
);

const userEmail = () => {
    let user = null;
    try {
        user = JSON.parse(localStorage.getItem('user') || 'null');
    } catch {}
    return user?.email?.toUpperCase() || "GUEST_CADET";
}