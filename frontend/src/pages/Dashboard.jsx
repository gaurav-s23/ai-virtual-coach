import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
    Zap, Mic, BookOpen, BarChart3, Layout, Settings, LogOut, 
    Flame, Target, ChevronRight, Activity, ShieldCheck, 
    Cpu, ListChecks, Trophy, ArrowUpRight, TrendingUp, Search, CalendarCheck
} from 'lucide-react';
import { motion } from 'framer-motion';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer, Radar as RadarArea } from 'recharts';

export default function Dashboard() {
    const navigate = useNavigate();
    const location = useLocation();
    
    // --- PERSISTENT LOGIC: Load data from LocalStorage ---
    const [stats, setStats] = useState(() => {
        const saved = localStorage.getItem('neural_stats');
        return saved ? JSON.parse(saved) : {
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
            ]
        };
    });

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
            const { score, total } = location.state.mockResult;
            const percentage = Math.round((score / total) * 100);
            
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
            
            {/* --- THE LIGHT BLUE / CYAN GLOW BACKGROUND --- */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-cyan-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-[0.03] pointer-events-none" />
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
                        {/* 1. Readiness Circular Gauge */}
                        <div className="bg-white/[0.02] border border-white/5 rounded-[3rem] p-10 flex flex-col items-center justify-center text-center relative group">
                            <div className="absolute inset-0 bg-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity rounded-[3rem]" />
                            <p className="text-[10px] font-black tracking-[0.3em] text-cyan-500 uppercase mb-8">Neural Readiness</p>
                            <div className="relative flex items-center justify-center">
                                <svg className="w-44 h-44 rotate-[-90deg]">
                                    <circle className="text-white/5" strokeWidth="12" stroke="currentColor" fill="transparent" r="80" cx="88" cy="88" />
                                    <circle className="text-cyan-500 transition-all duration-1000" strokeWidth="12" strokeDasharray={502} strokeDashoffset={502 - (502 * stats.readiness) / 100} strokeLinecap="round" stroke="currentColor" fill="transparent" r="80" cx="88" cy="88" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center rotate-[0deg]">
                                    <span className="text-6xl font-black text-white italic">{stats.readiness}<span className="text-xl text-cyan-500">%</span></span>
                                </div>
                            </div>
                            <div className="mt-8 flex gap-4 w-full">
                                <div className="flex-1 bg-black/20 p-4 rounded-2xl border border-white/5">
                                    <p className="text-[9px] text-gray-500 uppercase font-black">Prev Score</p>
                                    <p className="text-xl font-bold text-white">{stats.lastScore}</p>
                                </div>
                                <div className="flex-1 bg-black/20 p-4 rounded-2xl border border-white/5">
                                    <p className="text-[9px] text-gray-500 uppercase font-black">Avg Score</p>
                                    <p className="text-xl font-bold text-cyan-400">{stats.avgScore}</p>
                                </div>
                            </div>
                        </div>

                        {/* 2. Skill Radar Chart */}
                        <div className="bg-white/[0.02] border border-white/5 rounded-[3rem] p-8">
                            <p className="text-[10px] font-black tracking-[0.3em] text-blue-400 uppercase mb-6 text-center">Neural Matrix</p>
                            <div className="h-[280px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={stats.skills}>
                                        <PolarGrid stroke="#ffffff10" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 'bold' }} />
                                        <RadarArea name="Cadet" dataKey="A" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.4} />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* 3. Stats Column (Counters) */}
                        <div className="space-y-6">
                            <AttemptCard icon={<Mic />} label="Interview Probes" count={stats.interviews} color="cyan" />
                            <AttemptCard icon={<BookOpen />} label="Mock Assessments" count={stats.mocks} color="blue" />
                            <div className="bg-gradient-to-br from-cyan-600 to-blue-700 p-8 rounded-[2.5rem] shadow-xl relative overflow-hidden group">
                                <Cpu className="absolute -right-4 -bottom-4 w-32 h-32 text-white/10 group-hover:scale-110 transition-transform" />
                                <p className="text-[10px] font-black text-cyan-100 uppercase tracking-widest mb-2">Next Milestone</p>
                                <h4 className="text-2xl font-black text-white italic">Technical Principal</h4>
                                <p className="text-cyan-100/60 text-xs mt-4 leading-relaxed font-medium">Complete 5 more high-score interviews to unlock advanced system design probes.</p>
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
    const user = JSON.parse(localStorage.getItem('user'));
    return user ? user.email.toUpperCase() : "GUEST_CADET";
}