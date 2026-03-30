import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Mic, GraduationCap, MessageSquare, LayoutDashboard, 
  Settings, User, Plus, Star, Zap, Lock, ArrowRight, 
  Activity, Terminal, CheckCircle, Briefcase, Cpu, Globe,
  Target, ShieldCheck, TrendingUp, Search, Layers, Award
} from 'lucide-react';

const BackgroundEffect = () => (
    <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
      <div className="absolute top-[-10%] left-[-10%] w-[70%] h-[70%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-purple-600/10 blur-[120px] rounded-full animate-pulse delay-700" />
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
    </div>
);

const FeatureCard = ({ title, icon: Icon, color, path, isLoggedIn, desc, delay }) => {
  const navigate = useNavigate();
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: delay * 0.1 }}
      whileHover={{ y: -8 }}
      onClick={() => isLoggedIn ? navigate(path) : navigate('/auth')}
      className="group relative cursor-pointer"
    >
      <div className="relative aspect-square flex flex-col items-center justify-center p-8 bg-white/[0.03] backdrop-blur-2xl border border-white/10 rounded-[3rem] shadow-2xl transition-all group-hover:bg-white/[0.08] group-hover:border-blue-500/50 overflow-hidden">
        {!isLoggedIn && <div className="absolute top-6 right-6 text-white/20"><Lock size={16} /></div>}
        <div className={`absolute inset-0 bg-gradient-to-br ${color} opacity-0 group-hover:opacity-5 blur-3xl transition-opacity`} />
        <div className={`relative z-10 p-5 rounded-[1.5rem] bg-gradient-to-br ${color} mb-6 shadow-xl group-hover:scale-110 transition-transform`}>
          <Icon size={32} className="text-white" />
        </div>
        <h3 className="text-xl font-bold text-white tracking-tight">{title}</h3>
        <p className="text-[10px] text-blue-400 mt-2 font-black uppercase tracking-[0.2em] opacity-80">{desc}</p>
      </div>
    </motion.div>
  );
};

export default function Home() {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user'));
  const isLoggedIn = !!user;

  const features = [
    { title: "AI Interview", icon: Mic, color: "from-blue-600 to-indigo-600", path: "/setup-interview", desc: "8+5 Logic Simulation" },
    { title: "Mock Prep", icon: GraduationCap, color: "from-purple-600 to-pink-600", path: "/mock", desc: "Neural PDF Testing" },
    { title: "English Coach", icon: MessageSquare, color: "from-emerald-600 to-teal-600", path: "/english", desc: "Fluency Deep-Dive" },
    { title: "Intelligence", icon: LayoutDashboard, color: "from-orange-600 to-amber-600", path: "/dashboard", desc: "Skill Matrix Hub" },
  ];

  return (
    <div className="min-h-screen bg-[#020202] text-white font-sans selection:bg-blue-500/30 overflow-x-hidden">
      <BackgroundEffect />
      
      {/* --- HEADER --- */}
      <nav className="fixed top-0 left-0 right-0 z-50 p-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center bg-black/40 backdrop-blur-xl border border-white/10 p-4 rounded-[2rem] shadow-2xl">
            <div className="flex items-center gap-3 ml-4">
                <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg">
                    <Zap size={20} fill="white" className="text-white" />
                </div>
                <h1 className="text-xl font-black tracking-tighter uppercase text-white">
                    ai_virtual <span className="text-yellow-400">coach</span>
                </h1>
            </div>
            <div className="flex items-center gap-4 pr-4">
                {isLoggedIn ? (
                    <div className="flex items-center gap-4">
                        <span className="text-xs font-bold text-white font-mono bg-white/10 px-4 py-2 rounded-lg border border-white/10">
                            {user.email.split('@')[0].toUpperCase()}
                        </span>
                        <button onClick={() => {localStorage.clear(); window.location.reload();}} className="p-2.5 rounded-xl bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white transition-all">
                            <ArrowRight size={18} />
                        </button>
                    </div>
                ) : (
                    <button onClick={() => navigate('/auth')} className="bg-white text-black px-8 py-2.5 rounded-xl font-black text-xs uppercase tracking-widest hover:bg-yellow-400 hover:text-black transition-all">
                        Initialize
                    </button>
                )}
            </div>
        </div>
      </nav>

      {/* --- HERO SECTION --- */}
      <section className="relative pt-48 pb-32 px-6 max-w-7xl mx-auto text-center">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-bold text-[10px] uppercase tracking-widest mb-8">
            <Activity size={14} /> Neural Simulation Engine v2.5
        </motion.div>
        <motion.h2 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-7xl md:text-9xl font-black tracking-tight leading-[0.85] mb-8 text-white">
            Master the <br /> <span className="bg-gradient-to-r from-yellow-400 via-orange-400 to-yellow-600 bg-clip-text text-transparent italic font-serif">Future You.</span>
        </motion.h2>
        <p className="text-slate-300 max-w-2xl mx-auto text-xl leading-relaxed mb-12 font-medium">
            The world's first multi-modal AI career suite. From brutal mock interviews to neural aptitude testing, we build candidates that get hired.
        </p>
        <div className="flex justify-center gap-6">
            <button onClick={() => navigate('/setup-interview')} className="px-10 py-5 bg-blue-600 text-white rounded-2xl font-black uppercase text-xs tracking-widest hover:scale-105 transition-all shadow-2xl shadow-blue-600/30">Start Simulation</button>
            <button className="px-10 py-5 bg-white/5 border border-white/10 text-white rounded-2xl font-black uppercase text-xs tracking-widest hover:bg-white/10 transition-all">Watch Demo</button>
        </div>
      </section>

      {/* --- CORE CAPABILITIES (GRID) --- */}
      <section className="max-w-7xl mx-auto px-6 py-20 border-t border-white/5">
        <div className="text-center mb-20">
            <h2 className="text-4xl font-black text-white uppercase tracking-tighter">Core Modules</h2>
            <p className="text-slate-400 mt-2 font-mono text-sm uppercase tracking-widest">Select a specialized node to begin</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((f, i) => (
            <FeatureCard key={i} {...f} isLoggedIn={isLoggedIn} delay={i} />
          ))}
        </div>
      </section>

      {/* --- EXPANDED AIM & MISSION SECTION --- */}
      <section className="relative py-32 bg-white/[0.01]">
        <div className="max-w-5xl mx-auto px-6">
            <motion.div 
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="text-center space-y-8"
            >
                <div className="flex justify-center mb-4">
                    <span className="p-3 bg-yellow-400/10 border border-yellow-400/20 rounded-2xl text-yellow-500">
                        <Target size={40} />
                    </span>
                </div>
                <h2 className="text-5xl md:text-6xl font-black text-white tracking-tighter uppercase">
                    The Aim of <span className="text-yellow-400">ai_virtual coach</span>
                </h2>
                <div className="space-y-6 text-xl text-slate-300 leading-relaxed font-light">
                    <p>
                        The primary aim of this platform is to <strong className="text-white font-bold">democratize high-quality interview mentorship</strong>. For decades, elite career coaching was a luxury reserved for those who could afford expensive private mentors. We are breaking those barriers by putting a world-class, 24/7 technical mentor in the pocket of every student and professional.
                    </p>
                    <p>
                        Traditional mock interviews are often generic and lack the depth required for modern roles. Our platform changes this by <strong className="text-yellow-400 font-bold">synthesizing real-time feedback with role-specific technical challenges</strong>. Whether you are preparing for a FAANG engineering role or a consulting position, our AI simulator identifies your unique knowledge gaps, refines your communication nuances, and helps you master the psychological art of the technical interview.
                    </p>
                    <p>
                        Our mission is to bridge the gap between academic knowledge and industrial reality. By leveraging Large Language Models and proprietary <strong>"Stress-Test"</strong> algorithms, we simulate the high-pressure environment of actual interviews. Practice with purpose, improve with data, and transform from a candidate into a top-tier hire.
                    </p>
                </div>

                {/* Mission Sub-cards */}
                <div className="grid md:grid-cols-3 gap-6 pt-12">
                    {[
                        { icon: ShieldCheck, title: "Zero Bias", desc: "Purely merit-based evaluation without human subjectivity." },
                        { icon: TrendingUp, title: "Infinite Scale", desc: "Practice 100 times until your confidence is unbreakable." },
                        { icon: Search, title: "Deep Insight", desc: "Granular feedback on every word, gesture, and logic flow." }
                    ].map((item, idx) => (
                        <div key={idx} className="p-8 bg-white/5 border border-white/10 rounded-[2rem] text-left">
                            <item.icon className="text-yellow-400 mb-4" size={24} />
                            <h4 className="text-white font-bold mb-2">{item.title}</h4>
                            <p className="text-slate-400 text-sm leading-relaxed">{item.desc}</p>
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
      </section>

      {/* --- STATISTICS SECTION --- */}
      <section className="py-20 border-y border-white/5 bg-black">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-12 text-center">
            <div>
                <h3 className="text-5xl font-black text-yellow-400 mb-2">94%</h3>
                <p className="text-slate-500 font-bold uppercase text-[10px] tracking-widest">Confidence Boost</p>
            </div>
            <div>
                <h3 className="text-5xl font-black text-blue-500 mb-2">12k+</h3>
                <p className="text-slate-500 font-bold uppercase text-[10px] tracking-widest">Simulations Ran</p>
            </div>
            <div>
                <h3 className="text-5xl font-black text-purple-500 mb-2">85%</h3>
                <p className="text-slate-500 font-bold uppercase text-[10px] tracking-widest">Hiring Success</p>
            </div>
            <div>
                <h3 className="text-5xl font-black text-emerald-500 mb-2">24/7</h3>
                <p className="text-slate-500 font-bold uppercase text-[10px] tracking-widest">Neural Uptime</p>
            </div>
        </div>
      </section>

      {/* --- DETAILED CAPABILITIES --- */}
      <section className="max-w-7xl mx-auto px-6 py-32 space-y-40">
        
        {/* Capability 1 */}
        <div className="grid md:grid-cols-2 gap-20 items-center">
            <div className="space-y-6">
                <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center text-blue-500 border border-blue-500/20"><Mic size={32}/></div>
                <h3 className="text-5xl font-black text-white leading-tight">Brutal AI <br/> Interviews (8+5)</h3>
                <p className="text-slate-400 text-lg leading-relaxed">Our proprietary 8+5 logic probes your technical depth. After 8 primary questions, our AI pauses to analyze your "shaky" claims and generates 5 aggressive deep-dives to test technical honesty.</p>
                <ul className="space-y-3">
                    {['Real-time Voice Recognition', 'Context-Aware Follow-ups', 'Technical Accuracy Analysis'].map(li => (
                        <li key={li} className="flex items-center gap-3 text-white font-bold"><CheckCircle size={18} className="text-blue-500"/> {li}</li>
                    ))}
                </ul>
            </div>
            <div className="bg-blue-600/5 border border-blue-500/20 aspect-video rounded-[3rem] p-10 flex items-center justify-center relative overflow-hidden">
                <Terminal className="text-blue-500/20 absolute -bottom-10 -right-10 w-64 h-64" />
                <div className="text-center space-y-4 relative z-10">
                    <p className="text-blue-400 font-mono text-xs">AI_MODEL_STATUS: GENERATING_PROBES...</p>
                    <div className="w-64 h-2 bg-blue-900/30 rounded-full overflow-hidden">
                        <motion.div animate={{ x: [-256, 256] }} transition={{ repeat: Infinity, duration: 2 }} className="w-full h-full bg-blue-500" />
                    </div>
                </div>
            </div>
        </div>

        {/* Capability 2 */}
        <div className="grid md:grid-cols-2 gap-20 items-center">
            <div className="order-2 md:order-1 bg-purple-600/5 border border-purple-500/20 aspect-video rounded-[3rem] flex items-center justify-center">
                <Cpu className="text-purple-500 w-32 h-32 animate-pulse" />
            </div>
            <div className="order-1 md:order-2 space-y-6">
                <div className="w-16 h-16 bg-purple-600/20 rounded-2xl flex items-center justify-center text-purple-500 border border-purple-500/20"><GraduationCap size={32}/></div>
                <h3 className="text-5xl font-black text-white leading-tight">Neural PDF <br/> Assessments</h3>
                <p className="text-slate-400 text-lg leading-relaxed">Stop taking static tests. Our engine consumes Quant, Verbal, and Reasoning PDFs to synthesize a fresh MCQ test every single time you click start.</p>
                <ul className="space-y-3">
                    {['Automated PDF Parsing', 'Dynamic Score Weighting', 'Time-Pressure HUD Interface'].map(li => (
                        <li key={li} className="flex items-center gap-3 text-white font-bold"><CheckCircle size={18} className="text-purple-500"/> {li}</li>
                    ))}
                </ul>
            </div>
        </div>

        {/* Capability 3 */}
        <div className="grid md:grid-cols-2 gap-20 items-center">
            <div className="space-y-6">
                <div className="w-16 h-16 bg-emerald-600/20 rounded-2xl flex items-center justify-center text-emerald-500 border border-emerald-500/20"><Globe size={32}/></div>
                <h3 className="text-5xl font-black text-white leading-tight">Global Team <br/> Readiness</h3>
                <p className="text-slate-400 text-lg leading-relaxed">The English Coach doesn't just check grammar; it evaluates your readiness for international teams. Get rated on neural pace, vocabulary sophistication, and pronunciation clarity.</p>
                <button className="px-8 py-3 bg-emerald-600 text-white rounded-xl font-bold uppercase text-xs tracking-widest">Enter Fluency Coach</button>
            </div>
            <div className="bg-emerald-600/5 border border-emerald-500/20 aspect-video rounded-[3rem] p-10 flex flex-col items-center justify-center text-center">
                <Activity className="text-emerald-500 mb-4" size={48} />
                <h4 className="text-2xl font-black text-white tracking-tighter italic">"Your speech cadence is 92% optimized for remote collaboration."</h4>
            </div>
        </div>
      </section>

      {/* --- PROFESSIONAL FOOTER --- */}
      <footer className="bg-white/[0.02] border-t border-white/10 pt-20 pb-10">
        <div className="max-w-7xl mx-auto px-8 grid grid-cols-2 md:grid-cols-4 gap-12 mb-20">
            <div>
                <h4 className="text-white font-black uppercase tracking-tighter mb-8">For Candidates</h4>
                <ul className="space-y-4 text-slate-400 text-sm font-medium">
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Career Match</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Jobs in Bangalore</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Jobs in Mumbai</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Work From Home</li>
                </ul>
            </div>
            <div>
                <h4 className="text-white font-black uppercase tracking-tighter mb-8">Batches</h4>
                <ul className="space-y-4 text-slate-400 text-sm font-medium">
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">2026 Batch</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">2025 Batch</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">2024 Batch</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Alumni Network</li>
                </ul>
            </div>
            <div>
                <h4 className="text-white font-black uppercase tracking-tighter mb-8">Resources</h4>
                <ul className="space-y-4 text-slate-400 text-sm font-medium">
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">AI Simulation Docs</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Neural Status</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">System Logs</li>
                </ul>
            </div>
            <div>
                <h4 className="text-white font-black uppercase tracking-tighter mb-8">Legal</h4>
                <ul className="space-y-4 text-slate-400 text-sm font-medium">
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Privacy Policy</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Terms of Service</li>
                    <li className="hover:text-yellow-400 cursor-pointer transition-colors">Contact Support</li>
                </ul>
            </div>
        </div>
        
        <div className="max-w-7xl mx-auto px-8 pt-10 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">
                Copyright © 2025 ai_virtual_coach | Made with ❤️ for the Future
            </p>
            <div className="flex gap-8 text-[10px] font-black uppercase tracking-widest text-slate-400">
                <span className="flex items-center gap-2"><Cpu size={14}/> SYSTEM: STABLE</span>
                <span className="flex items-center gap-2"><Activity size={14}/> LATENCY: 24MS</span>
            </div>
        </div>
      </footer>
    </div>
  );
}