import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
    Users, BarChart3, CalendarCheck, Activity, Search, Filter,
    Zap, LogOut, Mail, ShieldCheck, Clock, TrendingUp, Globe
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import api from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorState from '../components/ErrorState';

export default function AdminPanel() {
    const navigate = useNavigate();
    
    const [adminData, setAdminData] = useState({
        total_users: 0,
        total_mock_sessions: 0,
        total_interview_sessions: 0,
        total_english_sessions: 0,
        total_requests_today: 0,
        all_users: []
    });
    
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filteredUsers, setFilteredUsers] = useState([]);

    useEffect(() => {
        fetchAdminStats();
    }, []);

    useEffect(() => {
        // Filter users based on search term
        if (searchTerm) {
            const filtered = adminData.all_users.filter(user => 
                user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                user.email.toLowerCase().includes(searchTerm.toLowerCase())
            );
            setFilteredUsers(filtered);
        } else {
            setFilteredUsers(adminData.all_users);
        }
    }, [searchTerm, adminData.all_users]);

    const fetchAdminStats = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.get('/api/admin/stats', {
                timeout: 10000,
            });
            setAdminData(res.data);
        } catch (err) {
            console.error('Admin stats fetch error:', err);
            setError('Failed to load admin data. Please check your permissions and try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('admin_token');
        navigate('/admin/login');
    };

    // Prepare daily activity data (mock data since we don't have daily stats from API yet)
    const dailyActivityData = [
        { date: 'Mon', requests: 45 },
        { date: 'Tue', requests: 52 },
        { date: 'Wed', requests: 38 },
        { date: 'Thu', requests: 65 },
        { date: 'Fri', requests: 48 },
        { date: 'Sat', requests: 32 },
        { date: 'Sun', requests: 28 },
    ];

    return (
        <div className="flex h-screen bg-slate-900 text-slate-200 font-sans overflow-hidden relative">
            
            {/* --- BACKGROUND --- */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-10%] left-[-10%] w-[60%] h-[60%] bg-purple-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-indigo-600/10 blur-[140px] rounded-full animate-pulse" />
                <div className="absolute inset-0 bg-gradient-to-br from-purple-900/10 via-transparent to-indigo-900/10 pointer-events-none" />
            </div>

            {/* --- SIDEBAR --- */}
            <aside className="w-72 border-r border-white/5 flex flex-col p-8 space-y-10 bg-black/20 backdrop-blur-3xl z-20">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl shadow-[0_0_20px_rgba(147,51,234,0.3)]">
                        <ShieldCheck size={22} className="text-white" />
                    </div>
                    <span className="font-black tracking-tighter text-2xl text-white uppercase italic">Admin<span className="text-purple-400">Hub</span></span>
                </div>
                
                <nav className="flex-1 space-y-2">
                    <NavItem icon={<BarChart3 size={18}/>} label="Overview" active />
                    <NavItem icon={<Users size={18}/>} label="Users" />
                    <NavItem icon={<Activity size={18}/>} label="Analytics" />
                    <NavItem icon={<CalendarCheck size={18}/>} label="Reports" />
                </nav>

                <button onClick={handleLogout} className="flex items-center gap-3 p-4 text-red-400/70 hover:text-red-400 hover:bg-red-500/5 rounded-2xl transition-all font-bold text-xs uppercase tracking-widest">
                    <LogOut size={16}/> <span>Logout</span>
                </button>
            </aside>

            {/* --- MAIN CONTENT --- */}
            <main className="flex-1 overflow-y-auto relative z-10 p-12 custom-scrollbar">
                <div className="max-w-7xl mx-auto space-y-10">
                    
                    {/* TOP HEADER */}
                    <header className="flex justify-between items-end">
                        <div>
                            <p className="text-purple-500 font-mono text-xs uppercase tracking-wider mb-2 font-black">Admin Panel</p>
                            <h1 className="text-5xl font-black text-white tracking-tighter">System Overview</h1>
                        </div>
                        <div className="flex gap-4">
                            <StatPill icon={<TrendingUp size={18}/>} label="TODAY'S REQUESTS" value={adminData.total_requests_today} color="green" />
                            <StatPill icon={<Users size={18}/>} label="TOTAL USERS" value={adminData.total_users} color="purple" />
                        </div>
                    </header>

                    {/* STATUS STRIP */}
                    {loading ? (
                        <LoadingSpinner label="Loading admin analytics" />
                    ) : error ? (
                        <ErrorState message={error} onRetry={fetchAdminStats} />
                    ) : null}

                    {/* STATS OVERVIEW CARDS */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <StatCard 
                            icon={<Users size={24} />}
                            title="Total Users"
                            value={adminData.total_users}
                            subtitle="Registered accounts"
                            color="purple"
                        />
                        <StatCard 
                            icon={<BarChart3 size={24} />}
                            title="Mock Sessions"
                            value={adminData.total_mock_sessions}
                            subtitle="Total attempts"
                            color="cyan"
                        />
                        <StatCard 
                            icon={<Mic size={24} />}
                            title="Interviews"
                            value={adminData.total_interview_sessions}
                            subtitle="Completed sessions"
                            color="blue"
                        />
                        <StatCard 
                            icon={<Globe size={24} />}
                            title="English Sessions"
                            value={adminData.total_english_sessions}
                            subtitle="Practice sessions"
                            color="green"
                        />
                    </div>

                    {/* DAILY REQUEST ACTIVITY */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex items-center gap-3 mb-6">
                            <Activity className="text-purple-400" />
                            <h2 className="text-2xl font-black text-white">Daily Request Activity (Last 7 Days)</h2>
                        </div>
                        
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={dailyActivityData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                <XAxis dataKey="date" tick={{ fill: '#9CA3AF' }} />
                                <YAxis tick={{ fill: '#9CA3AF' }} />
                                <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151' }} />
                                <Line type="monotone" dataKey="requests" stroke="#8B5CF6" strokeWidth={3} dot={{ fill: '#8B5CF6', r: 6 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    {/* USERS TABLE */}
                    <div className="bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 backdrop-blur-2xl">
                        <div className="flex justify-between items-center mb-6">
                            <div className="flex items-center gap-3">
                                <Users className="text-purple-400" />
                                <h2 className="text-2xl font-black text-white">Users Management</h2>
                            </div>
                            
                            <div className="flex gap-4 items-center">
                                <div className="relative">
                                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
                                    <input
                                        type="text"
                                        placeholder="Search users..."
                                        value={searchTerm}
                                        onChange={(e) => setSearchTerm(e.target.value)}
                                        className="pl-10 pr-4 py-2 bg-black/40 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-purple-500/30"
                                    />
                                </div>
                                <button className="flex items-center gap-2 px-4 py-2 bg-purple-500/10 border border-purple-500/20 rounded-xl text-purple-400 hover:bg-purple-500/20 transition-all">
                                    <Filter size={16} />
                                    Filter
                                </button>
                            </div>
                        </div>
                        
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-white/10">
                                        <th className="text-left py-3 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Name</th>
                                        <th className="text-left py-3 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Email</th>
                                        <th className="text-left py-3 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Skills</th>
                                        <th className="text-left py-3 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Joined Date</th>
                                        <th className="text-left py-3 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Sessions</th>
                                        <th className="text-left py-3 px-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Last Active</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredUsers.map((user, index) => (
                                        <motion.tr 
                                            key={user.id}
                                            initial={{ opacity: 0, x: -20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: index * 0.05 }}
                                            className="border-b border-white/5 hover:bg-white/5 transition-colors"
                                        >
                                            <td className="py-4 px-4">
                                                <div className="flex items-center gap-3">
                                                    <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center">
                                                        <span className="text-purple-400 text-xs font-bold">
                                                            {user.name.charAt(0).toUpperCase()}
                                                        </span>
                                                    </div>
                                                    <span className="text-white font-medium">{user.name}</span>
                                                </div>
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="flex items-center gap-2">
                                                    <Mail size={14} className="text-gray-400" />
                                                    <span className="text-gray-300">{user.email}</span>
                                                </div>
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="flex flex-wrap gap-1">
                                                    {user.resume_skills.length > 0 ? (
                                                        user.resume_skills.slice(0, 3).map((skill, idx) => (
                                                            <span key={idx} className="px-2 py-1 bg-purple-500/10 border border-purple-500/20 rounded text-xs text-purple-400">
                                                                {skill}
                                                            </span>
                                                        ))
                                                    ) : (
                                                        <span className="text-gray-500 text-sm">No skills listed</span>
                                                    )}
                                                    {user.resume_skills.length > 3 && (
                                                        <span className="text-gray-500 text-xs">+{user.resume_skills.length - 3} more</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="flex items-center gap-2">
                                                    <CalendarCheck size={14} className="text-gray-400" />
                                                    <span className="text-gray-300">{user.joined_date}</span>
                                                </div>
                                            </td>
                                            <td className="py-4 px-4">
                                                <span className="text-white font-mono">0</span>
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="flex items-center gap-2">
                                                    <Clock size={14} className="text-gray-400" />
                                                    <span className="text-gray-300">Recently</span>
                                                </div>
                                            </td>
                                        </motion.tr>
                                    ))}
                                </tbody>
                            </table>
                            
                            {filteredUsers.length === 0 && !loading && (
                                <div className="text-center py-12">
                                    <Users className="mx-auto text-gray-500 mb-4" size={48} />
                                    <p className="text-gray-500">
                                        {searchTerm ? 'No users found matching your search' : 'No users available'}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                </div>
            </main>
        </div>
    );
}

// --- SUB-COMPONENTS ---

const NavItem = ({ icon, label, active = false }) => (
    <div className={`flex items-center gap-4 p-4 rounded-2xl transition-all cursor-pointer group ${active ? 'bg-purple-500/10 text-white border border-purple-500/20' : 'text-slate-500 hover:bg-white/5'}`}>
        <div className={`${active ? 'text-purple-400 shadow-[0_0_10px_rgba(147,51,234,0.4)]' : 'group-hover:text-purple-400'} transition-colors`}>{icon}</div>
        <span className="text-sm font-black uppercase tracking-widest">{label}</span>
    </div>
);

const colorMap = {
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-500', textMuted: 'text-purple-500/60' },
    green: { bg: 'bg-green-500/10', border: 'border-green-500/20', text: 'text-green-500', textMuted: 'text-green-500/60' },
    cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-500', textMuted: 'text-cyan-500/60' },
    blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/20', text: 'text-blue-500', textMuted: 'text-blue-500/60' },
};

const StatPill = ({ icon, label, value, color }) => (
    <div className={`${(colorMap[color] || colorMap.purple).bg} ${(colorMap[color] || colorMap.purple).border} px-6 py-4 rounded-[2rem] flex items-center gap-4`}>
        <div className={(colorMap[color] || colorMap.purple).text}>{icon}</div>
        <div>
            <p className={`text-xs font-black ${(colorMap[color] || colorMap.purple).textMuted} uppercase tracking-widest leading-none`}>{label}</p>
            <p className="text-xl font-black font-mono leading-none mt-1.5 text-white">{value}</p>
        </div>
    </div>
);

const StatCard = ({ icon, title, value, subtitle, color }) => (
    <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${(colorMap[color] || colorMap.purple).bg} ${(colorMap[color] || colorMap.purple).border} p-6 rounded-2xl backdrop-blur-2xl`}
    >
        <div className={`${(colorMap[color] || colorMap.purple).text} mb-4`}>{icon}</div>
        <div className="text-3xl font-black text-white mb-1">{value}</div>
        <div className="text-lg font-medium text-white mb-1">{title}</div>
        <div className="text-sm text-gray-400">{subtitle}</div>
    </motion.div>
);
