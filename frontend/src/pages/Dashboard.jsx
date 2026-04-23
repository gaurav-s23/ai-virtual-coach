import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
    Zap, Mic, BookOpen, Layout, LogOut,
    Flame, Target, Activity, TrendingUp, TrendingDown,
    Cpu, Trophy, CalendarCheck, Gauge, AlertTriangle,
    BarChart3, Users, Clock,Globe, Award, Code, ShieldCheck
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import api from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorState from '../components/ErrorState';
import StatCard from '../components/StatCard';

export default function Dashboard() {
    const navigate = useNavigate();
    const location = useLocation();
    
    const [dashboardData, setDashboardData] = useState({
        mock: { total_attempted: 0, completed: 0, abandoned: 0, avg_score: 0, section_scores: { quant: 0, verbal: 0, reasoning: 0, coding: 0 } },
        interview: { total_attempted: 0, avg_score: 0, fluency_score: 0, weak_areas: [] },
        english: { total_attempted: 0, avg_fluency_score: 0 },
        daily_activity: [],
        overall_weak_areas: []
    });
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);

    const [userId, setUserId] = useState(null);

    // Get user ID from localStorage safely
    useEffect(() => {
        try {
            const userStr = localStorage.getItem('user');
            const user = userStr ? JSON.parse(userStr) : null;
            
            if (!user || !user.id) {
                setError('User session not found. Please log in again.');
                navigate('/auth');
                return;
            }
            
            setUserId(user.id);
            
            // Check if user is admin
            setIsAdmin(user.email === 'admin@example.com' || user.role === 'admin');
        } catch (error) {
            console.error('Failed to get user ID:', error);
            setError('Session corrupted. Please log in again.');
            navigate('/auth');
        }
    }, [navigate]);

    const fetchDashboardStats = async () => {
        if (!userId) return;
        
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/api/user/dashboard-stats', {
                timeout: 8000,
            });
            setDashboardData(res.data);
        } catch (err) {
            console.error('Dashboard fetch error:', err);
            setError('Failed to load dashboard data. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (userId) {
            fetchDashboardStats();
        }
    }, [userId]);

    // Calculate completion rates
    const mockCompletionRate = dashboardData.mock.total_attempted > 0 
        ? Math.round((dashboardData.mock.completed / dashboardData.mock.total_attempted) * 100) 
        : 0;
    
    const interviewCompletionRate = dashboardData.interview.total_attempted > 0 
        ? Math.round(((dashboardData.interview.total_attempted - (dashboardData.mock.total_attempted - dashboardData.mock.completed)) / dashboardData.interview.total_attempted) * 100) 
        : 0;

    const englishCompletionRate = dashboardData.english.total_attempted > 0 
        ? Math.round((dashboardData.english.total_attempted * 0.8) * 100) // Estimate
        : 0;

    // Prepare chart data
    const radarData = [
        { subject: 'Quant', score: dashboardData.mock.section_scores.quant, fullMark: 100 },
        { subject: 'Verbal', score: dashboardData.mock.section_scores.verbal, fullMark: 100 },
        { subject: 'Reasoning', score: dashboardData.mock.section_scores.reasoning, fullMark: 100 },
        { subject: 'Coding', score: dashboardData.mock.section_scores.coding, fullMark: 100 },
    ];

    const dailyActivityData = dashboardData.daily_activity.map(day => ({
        date: new Date(day.date).toLocaleDateString('en', { weekday: 'short' }),
        mock: day.mock_count,
        interview: day.interview_count,
        english: day.english_count,
        total: day.mock_count + day.interview_count + day.english_count
    }));

    const userEmail = () => {
        let user = null;
        try {
            user = JSON.parse(localStorage.getItem('user') || 'null');
        } catch {}
        return user?.email?.toUpperCase() || "GUEST_CADET";
    };

    return (
        <div className="flex h-screen bg-slate-900 text-slate-200 font-sans overflow-hidden relative">
            
            {/* --- BACKGROUND --- */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-cyan-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute inset-0 bg-gradient-to-br from-cyan-900/10 via-transparent to-blue-900/10 pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-tl from-purple-900/10 via-transparent to-indigo-900/10 pointer-events-none" />
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
                    {isAdmin && (
                        <NavItem 
                            icon={<ShieldCheck size={18}/>} 
                            label="Admin Panel" 
                            onClick={() => navigate('/admin')}
                        />
                    )}
                </nav>

                <button onClick={() => navigate('/')} className="flex items-center gap-3 p-4 text-red-400/70 hover:text-red-400 hover:bg-red-500/5 rounded-2xl transition-all font-bold text-xs uppercase tracking-widest">
                    <LogOut size={16}/> <span>Terminate</span>
                </button>
            </aside>

            {/* --- MAIN CONTENT --- */}
            <main className="flex-1 overflow-y-auto relative z-10 p-12 custom-scrollbar">
                <div className="max-w-7xl mx-auto space-y-10">
                    
                    {/* TOP HEADER */}
                    <header className="flex justify-between items-end">
                        <div>
                            <p className="text-cyan-500 font-mono text-xs uppercase tracking-wider mb-2 font-black">System Ready: {userEmail()}</p>
                            <h1 className="text-5xl font-black text-white tracking-tighter">Command Centre</h1>
                        </div>
                        <div className="flex gap-4">
                            <StatPill icon={<Flame size={18}/>} label="ACTIVITY STREAK" value="7 DAYS" color="orange" />
                            <StatPill icon={<Trophy size={18}/>} label="TOTAL SESSIONS" value={dashboardData.mock.total_attempted + dashboardData.interview.total_attempted + dashboardData.english.total_attempted} color="cyan" />
                        </div>
                    </header>

                    {/* STATUS STRIP */}
                    {loading ? (
                        <LoadingSpinner label="Syncing dashboard analytics" />
                    ) : error ? (
                        <ErrorState message={error} onRetry={fetchDashboardStats} />
                    ) : null}

                    {/* SECTION 1 - TOTAL ACTIVITY SUMMARY */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <ActivityCard 
                            icon={<BookOpen size={24} />}
                            title="Mock Tests"
                            count={dashboardData.mock.total_attempted}
                            completionRate={mockCompletionRate}
                            color="violet"
                        />
                        <ActivityCard 
                            icon={<Mic size={24} />}
                            title="Interviews"
                            count={dashboardData.interview.total_attempted}
                            completionRate={interviewCompletionRate}
                            color="blue"
                        />
                        <ActivityCard 
                            icon={<Globe size={24} />}
                            title="English Sessions"
                            count={dashboardData.english.total_attempted}
                            completionRate={englishCompletionRate}
                            color="cyan"
                        />
                        <ActivityCard 
                            icon={<Code size={24} />}
                            title="Coding Tests"
                            count={0}
                            completionRate={0}
                            color="green"
                        />
                    </div>

                    {/* SECTION 2 - MOCK TEST ANALYTICS */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex items-center gap-3 mb-6">
                            <BookOpen className="text-violet-400" />
                            <h2 className="text-2xl font-black text-white">Mock Test Analytics</h2>
                        </div>
                        
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <div>
                                <h3 className="text-lg font-bold text-white mb-4">Section Performance</h3>
                                <ResponsiveContainer width="100%" height={300}>
                                    <RadarChart data={radarData}>
                                        <PolarGrid stroke="#374151" />
                                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                                        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#9CA3AF', fontSize: 10 }} />
                                        <Radar name="Score" dataKey="score" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.6} />
                                        <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                            
                            <div>
                                <h3 className="text-lg font-bold text-white mb-4">Section Breakdown</h3>
                                <div className="space-y-4">
                                    {Object.entries(dashboardData.mock.section_scores).map(([section, score]) => (
                                        <div key={section} className="space-y-2">
                                            <div className="flex justify-between text-sm">
                                                <span className="text-gray-400 capitalize">{section}</span>
                                                <span className="text-white font-mono">{score}%</span>
                                            </div>
                                            <div className="w-full h-2 bg-black/40 rounded-full overflow-hidden">
                                                <motion.div 
                                                    initial={{ width: 0 }} 
                                                    animate={{ width: `${score}%` }}
                                                    className={`h-full rounded-full ${
                                                        score >= 70 ? 'bg-green-500' : score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                                                    }`} 
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* SECTION 3 - INTERVIEW ANALYTICS */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex items-center gap-3 mb-6">
                            <Mic className="text-blue-400" />
                            <h2 className="text-2xl font-black text-white">Interview Analytics</h2>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div className="space-y-6">
                                <div>
                                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Average Score</h3>
                                    <div className="flex items-center gap-4">
                                        <div className="text-4xl font-black text-white">{dashboardData.interview.avg_score.toFixed(1)}%</div>
                                        <Gauge className="text-blue-400" />
                                    </div>
                                </div>
                                
                                <div>
                                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Fluency Score</h3>
                                    <div className="flex items-center gap-4">
                                        <div className="text-4xl font-black text-white">{dashboardData.interview.fluency_score.toFixed(1)}%</div>
                                        <TrendingUp className="text-green-400" />
                                    </div>
                                </div>
                            </div>
                            
                            <div>
                                <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Weak Areas</h3>
                                <div className="space-y-2">
                                    {dashboardData.interview.weak_areas.length > 0 ? (
                                        dashboardData.interview.weak_areas.map((area, index) => (
                                            <div key={index} className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
                                                <AlertTriangle className="text-red-400" size={16} />
                                                <span className="text-red-400 text-sm font-medium">{area}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-gray-500 text-sm">No weak areas identified</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* SECTION 4 - ENGLISH PRACTICE */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex items-center gap-3 mb-6">
                            <Globe className="text-cyan-400" />
                            <h2 className="text-2xl font-black text-white">English Practice</h2>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="text-center p-6 bg-cyan-500/10 border border-cyan-500/20 rounded-2xl">
                                <div className="text-3xl font-black text-cyan-400">{dashboardData.english.total_attempted}</div>
                                <div className="text-sm text-gray-400 mt-2">Sessions Completed</div>
                            </div>
                            <div className="text-center p-6 bg-green-500/10 border border-green-500/20 rounded-2xl">
                                <div className="text-3xl font-black text-green-400">{dashboardData.english.avg_fluency_score.toFixed(1)}%</div>
                                <div className="text-sm text-gray-400 mt-2">Avg Fluency Score</div>
                            </div>
                            <div className="text-center p-6 bg-blue-500/10 border border-blue-500/20 rounded-2xl">
                                <div className="text-3xl font-black text-blue-400">5</div>
                                <div className="text-sm text-gray-400 mt-2">Topics Practiced</div>
                            </div>
                        </div>
                    </div>

                    {/* SECTION 5 - DAILY ACTIVITY */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex items-center gap-3 mb-6">
                            <CalendarCheck className="text-green-400" />
                            <h2 className="text-2xl font-black text-white">Daily Activity (Last 7 Days)</h2>
                        </div>
                        
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={dailyActivityData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis dataKey="date" tick={{ fill: '#9CA3AF' }} />
                                <YAxis tick={{ fill: '#9CA3AF' }} />
                                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                                <Bar dataKey="mock" fill="#8B5CF6" name="Mock Tests" />
                                <Bar dataKey="interview" fill="#3B82F6" name="Interviews" />
                                <Bar dataKey="english" fill="#06B6D4" name="English" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    {/* SECTION 6 - WEAK AREAS & RECOMMENDATIONS */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex items-center gap-3 mb-6">
                            <AlertTriangle className="text-orange-400" />
                            <h2 className="text-2xl font-black text-white">Weak Areas & Recommendations</h2>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div>
                                <h3 className="text-lg font-bold text-white mb-4">Areas to Improve</h3>
                                <div className="space-y-3">
                                    {dashboardData.overall_weak_areas.length > 0 ? (
                                        dashboardData.overall_weak_areas.map((area, index) => (
                                            <div key={index} className="flex items-center gap-3 p-4 bg-orange-500/10 border border-orange-500/20 rounded-xl">
                                                <AlertTriangle className="text-orange-400" size={20} />
                                                <div>
                                                    <div className="text-white font-medium">{area}</div>
                                                    <div className="text-gray-400 text-sm">Needs focused practice</div>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-gray-500">No weak areas identified. Great job!</div>
                                    )}
                                </div>
                            </div>
                            
                            <div>
                                <h3 className="text-lg font-bold text-white mb-4">Actionable Tips</h3>
                                <div className="space-y-3">
                                    {dashboardData.overall_weak_areas.includes('Technical Skills') && (
                                        <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                                            <div className="text-blue-400 font-medium">Practice More Quant</div>
                                            <div className="text-gray-400 text-sm mt-1">Focus on technical questions and problem-solving</div>
                                        </div>
                                    )}
                                    {dashboardData.overall_weak_areas.includes('Fluency') && (
                                        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
                                            <div className="text-green-400 font-medium">Work on Fluency</div>
                                            <div className="text-gray-400 text-sm mt-1">Practice speaking exercises and English sessions</div>
                                        </div>
                                    )}
                                    {dashboardData.overall_weak_areas.includes('Communication') && (
                                        <div className="p-4 bg-purple-500/10 border border-purple-500/20 rounded-xl">
                                            <div className="text-purple-400 font-medium">Improve Communication</div>
                                            <div className="text-gray-400 text-sm mt-1">Focus on clarity and structure in responses</div>
                                        </div>
                                    )}
                                    {dashboardData.overall_weak_areas.length === 0 && (
                                        <div className="p-4 bg-green-500/10 border border-green-500/20 rounded-xl">
                                            <div className="text-green-400 font-medium">Keep Up the Great Work!</div>
                                            <div className="text-gray-400 text-sm mt-1">You're performing excellently across all areas</div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}

// --- SUB-COMPONENTS ---

const NavItem = ({ icon, label, active = false, onClick }) => (
    <div 
        onClick={onClick}
        className={`flex items-center gap-4 p-4 rounded-2xl transition-all cursor-pointer group ${active ? 'bg-cyan-500/10 text-white border border-cyan-500/20' : 'text-slate-500 hover:bg-white/5'}`}
    >
        <div className={`${active ? 'text-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.4)]' : 'group-hover:text-cyan-400'} transition-colors`}>{icon}</div>
        <span className="text-sm font-black uppercase tracking-widest">{label}</span>
    </div>
);

const colorMap = {
    cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-500', textMuted: 'text-cyan-500/60' },
    orange: { bg: 'bg-orange-500/10', border: 'border-orange-500/20', text: 'text-orange-500', textMuted: 'text-orange-500/60' },
    blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-500', textMuted: 'text-blue-500/60' },
    violet: { bg: 'bg-violet-500/10', border: 'border-violet-500/20', text: 'text-violet-500', textMuted: 'text-violet-500/60' },
    green: { bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-500', textMuted: 'text-green-500/60' },
};

const StatPill = ({ icon, label, value, color }) => (
    <div className={`${(colorMap[color] || colorMap.cyan).bg} ${(colorMap[color] || colorMap.cyan).border} px-6 py-4 rounded-[2rem] flex items-center gap-4`}>
        <div className={(colorMap[color] || colorMap.cyan).text}>{icon}</div>
        <div>
            <p className={`text-xs font-black ${(colorMap[color] || colorMap.cyan).textMuted} uppercase tracking-widest leading-none`}>{label}</p>
            <p className="text-xl font-black font-mono leading-none mt-1.5 text-white">{value}</p>
        </div>
    </div>
);

const ActivityCard = ({ icon, title, count, completionRate, color }) => (
    <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${(colorMap[color] || colorMap.cyan).bg} ${(colorMap[color] || colorMap.cyan).border} p-6 rounded-2xl backdrop-blur-2xl`}
    >
        <div className="flex items-center justify-between mb-4">
            <div className={`${(colorMap[color] || colorMap.cyan).text}`}>{icon}</div>
            <div className={`text-xs font-bold ${(colorMap[color] || colorMap.cyan).textMuted} uppercase tracking-wider`}>
                {completionRate > 0 ? `${completionRate}% Complete` : 'No Data'}
            </div>
        </div>
        <div className="text-3xl font-black text-white mb-1">{count}</div>
        <div className="text-sm text-gray-400 font-medium">{title}</div>
        {completionRate > 0 && (
            <div className="mt-3 w-full h-1.5 bg-black/40 rounded-full overflow-hidden">
                <motion.div 
                    initial={{ width: 0 }} 
                    animate={{ width: `${completionRate}%` }}
                    className={`h-full rounded-full ${(colorMap[color] || colorMap.cyan).text} bg-opacity-60`} 
                />
            </div>
        )}
    </motion.div>
);
