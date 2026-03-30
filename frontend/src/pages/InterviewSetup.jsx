import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { 
    Upload, Play, Loader2, ChevronRight, Sparkles, Zap, Shield, 
    CheckCircle2, Briefcase, Clock, GraduationCap, Video, Mic, ShieldCheck 
} from "lucide-react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";

const BackgroundEffect = () => (
  <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
    <div className="absolute top-[-10%] left-[-10%] w-[70%] h-[70%] bg-blue-600/10 blur-[120px] rounded-full animate-pulse" />
    <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] bg-purple-600/10 blur-[120px] rounded-full animate-pulse delay-700" />
    <div className="absolute inset-0 opacity-[0.02] pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')]" />
  </div>
);

const StepIndicator = ({ currentStep }) => (
  <div className="flex items-center gap-2 mb-8">
    {[1, 2, 3, 4, 5].map((s) => (
      <div key={s} className="flex-1 h-1 rounded-full overflow-hidden bg-white/10">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: s <= currentStep ? "100%" : "0%" }}
          className="h-full bg-gradient-to-r from-blue-500 to-indigo-500"
        />
      </div>
    ))}
  </div>
);

export default function InterviewSetup() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [hardwareGranted, setHardwareGranted] = useState({ cam: false, mic: false });
  
  const [data, setData] = useState({ 
    role: "", 
    type: "Technical", 
    experience: "Intermediate", 
    duration: "30 mins",
    jd: "", 
    resume: null 
  });

  const checkPermissions = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setHardwareGranted({ cam: true, mic: true });
      stream.getTracks().forEach(track => track.stop());
    } catch (err) {
      alert("Please grant Camera and Microphone access to proceed with the simulation.");
    }
  };

  const finalizeSetup = async () => {
    if (!data.resume) return alert("Please upload a resume");
    setLoading(true);
    
    const formData = new FormData();
    formData.append("resume", data.resume);
    formData.append("jd", data.jd);
    formData.append("role", data.role);
    formData.append("experience", data.experience);
    formData.append("type", data.type);

    try {
      const res = await axios.post("http://127.0.0.1:8000/api/start-interview", formData);
      // Moving to simulation with full blueprint context
      navigate("/live-interview", { 
        state: { 
            ...res.data, 
            role: data.role, 
            context: data.jd 
        } 
      });
    } catch (err) {
      alert("Neural Link Failed: Server unreachable.");
    } finally {
      setLoading(false);
    }
  };

  const variants = {
    enter: { opacity: 0, x: 20 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -20 },
  };

  return (
    <div className="min-h-screen bg-[#030303] text-white font-sans selection:bg-blue-500/30 overflow-x-hidden">
      <BackgroundEffect />

      {/* NAV BAR */}
      <nav className="relative z-20 flex justify-between items-center px-10 py-8 max-w-[1400px] mx-auto">
        <div className="flex items-center gap-3 group cursor-pointer">
          <div className="relative p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-500/20">
            <Zap size={22} fill="white" />
          </div>
          <span className="text-xl font-bold tracking-tight uppercase">ai_virtual<span className="text-blue-500">coach</span></span>
        </div>
        <div className="px-5 py-2 rounded-full border border-white/5 bg-white/[0.02] backdrop-blur-xl text-[10px] font-black tracking-widest text-gray-400">
           AUTH_TOKEN: <span className="text-emerald-500 underline">VALID_SESSION</span>
        </div>
      </nav>

      <main className="relative z-10 max-w-[1400px] mx-auto px-8 pt-12 pb-32 grid lg:grid-cols-[1.1fr_1fr] gap-20 items-start">
        
        {/* LEFT SIDE: BLUEPRINT COPY */}
        <div className="lg:sticky lg:top-32 space-y-10">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 font-bold tracking-widest text-[10px] uppercase">
              <Sparkles size={14} /> Path to Senior Architect
            </div>
            <h1 className="text-6xl xl:text-8xl font-black leading-[0.9] tracking-tighter">
              Calibrate Your <br />
              <span className="bg-gradient-to-r from-white via-blue-400 to-indigo-500 bg-clip-text text-transparent italic font-serif">Career Neural.</span>
            </h1>
            <p className="text-lg text-gray-500 max-w-lg leading-relaxed">
              Our simulation engine generates dynamic, high-pressure technical probes. 
              Upload your persona and let the coach find your weaknesses.
            </p>
          </motion.div>

          <div className="grid grid-cols-2 gap-8 pt-10 border-t border-white/5 max-w-md">
            <div>
                <p className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-1">Precision</p>
                <p className="text-2xl font-bold italic">Gemini 1.5 Flash</p>
            </div>
            <div>
                <p className="text-[10px] font-black text-gray-600 uppercase tracking-widest mb-1">Latency</p>
                <p className="text-2xl font-bold italic">&lt; 800ms</p>
            </div>
          </div>
        </div>

        {/* RIGHT SIDE: ONBOARDING CARD */}
        <div className="relative group">
          <div className="absolute -inset-[1px] bg-gradient-to-b from-blue-500/20 to-transparent rounded-[3rem] opacity-50" />
          <div className="relative bg-[#0A0A0B]/80 border border-white/10 backdrop-blur-3xl rounded-[3rem] p-10 lg:p-14 shadow-2xl overflow-hidden">
            <StepIndicator currentStep={step} />

            <AnimatePresence mode="wait">
              {/* STEP 1: JOB TYPE & ROLE */}
              {step === 1 && (
                <motion.div key="1" variants={variants} initial="enter" animate="center" exit="exit" className="space-y-8">
                  <div className="space-y-2">
                    <h2 className="text-3xl font-bold tracking-tight">Step 1: The Target</h2>
                    <p className="text-gray-500">Define your domain and specific role.</p>
                  </div>
                  <div className="flex p-1 bg-white/5 rounded-2xl border border-white/5">
                    {["Technical", "Non-Tech"].map(t => (
                        <button key={t} onClick={() => setData({...data, type: t})} className={`flex-1 py-3 rounded-xl text-xs font-bold transition-all ${data.type === t ? 'bg-blue-600 text-white' : 'text-gray-500'}`}>
                            {t.toUpperCase()}
                        </button>
                    ))}
                  </div>
                  <div className="relative group/input">
                    <Briefcase className="absolute left-6 top-1/2 -translate-y-1/2 text-gray-600" size={20} />
                    <input
                      placeholder="e.g. Senior Software Architect"
                      className="w-full bg-white/[0.03] border border-white/10 rounded-2xl pl-16 pr-8 py-6 text-xl outline-none focus:border-blue-500/50 transition-all"
                      onChange={(e) => setData({ ...data, role: e.target.value })}
                    />
                  </div>
                  <button onClick={() => setStep(2)} disabled={!data.role} className="w-full bg-white text-black py-5 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-blue-500 hover:text-white transition-all disabled:opacity-50">
                    Next Phase
                  </button>
                </motion.div>
              )}

              {/* STEP 2: EXPERIENCE & DURATION */}
              {step === 2 && (
                <motion.div key="2" variants={variants} initial="enter" animate="center" exit="exit" className="space-y-8">
                  <div className="space-y-2">
                    <h2 className="text-3xl font-bold tracking-tight">Step 2: Intensity</h2>
                    <p className="text-gray-500">Set the seniority and simulation length.</p>
                  </div>
                  <div className="space-y-4">
                    <label className="text-[10px] font-black uppercase text-gray-500 tracking-widest ml-2">Seniority Level</label>
                    <div className="grid grid-cols-3 gap-3">
                        {["Junior", "Intermediate", "Expert"].map(l => (
                            <button key={l} onClick={() => setData({...data, experience: l})} className={`py-4 rounded-xl border text-[10px] font-black transition-all ${data.experience === l ? 'border-blue-500 bg-blue-500/10 text-white' : 'border-white/5 bg-white/5 text-gray-500'}`}>
                                {l.toUpperCase()}
                            </button>
                        ))}
                    </div>
                  </div>
                  <div className="space-y-4">
                    <label className="text-[10px] font-black uppercase text-gray-500 tracking-widest ml-2">Simulation Duration</label>
                    <div className="grid grid-cols-3 gap-3">
                        {["15 mins", "30 mins", "45 mins"].map(d => (
                            <button key={d} onClick={() => setData({...data, duration: d})} className={`py-4 rounded-xl border text-[10px] font-black transition-all ${data.duration === d ? 'border-blue-500 bg-blue-500/10 text-white' : 'border-white/5 bg-white/5 text-gray-500'}`}>
                                {d.toUpperCase()}
                            </button>
                        ))}
                    </div>
                  </div>
                  <button onClick={() => setStep(3)} className="w-full bg-white text-black py-5 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-blue-500 hover:text-white transition-all">
                    Synchronize Logic
                  </button>
                </motion.div>
              )}

              {/* STEP 3: JOB DESCRIPTION */}
              {step === 3 && (
                <motion.div key="3" variants={variants} initial="enter" animate="center" exit="exit" className="space-y-8">
                  <div className="space-y-2">
                    <h2 className="text-3xl font-bold tracking-tight">Step 3: JD Analysis</h2>
                    <p className="text-gray-500">Paste the Job Description for neural context.</p>
                  </div>
                  <textarea
                    placeholder="Paste the requirements here..."
                    className="w-full bg-white/[0.03] border border-white/10 rounded-2xl px-8 py-6 h-60 text-lg transition-all outline-none focus:border-blue-500/50 resize-none leading-relaxed"
                    onChange={(e) => setData({ ...data, jd: e.target.value })}
                  />
                  <button onClick={() => setStep(4)} className="w-full bg-white text-black py-5 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-blue-500 hover:text-white transition-all">
                    Proceed to Dossier
                  </button>
                </motion.div>
              )}

              {/* STEP 4: RESUME UPLOAD */}
              {step === 4 && (
                <motion.div key="4" variants={variants} initial="enter" animate="center" exit="exit" className="space-y-8">
                   <div className="space-y-2">
                    <h2 className="text-3xl font-bold tracking-tight">Step 4: Personal Bio</h2>
                    <p className="text-gray-500">Upload your PDF resume to calibrate the 8+5 logic.</p>
                  </div>
                  <label className="relative flex flex-col items-center justify-center w-full h-64 border-2 border-dashed border-white/10 hover:border-blue-500/40 rounded-[2rem] cursor-pointer bg-white/[0.02] group/upload transition-all overflow-hidden">
                    <input type="file" className="hidden" accept=".pdf" onChange={(e) => setData({ ...data, resume: e.target.files[0] })} />
                    {data.resume ? (
                        <div className="text-center animate-in zoom-in duration-300">
                          <div className="p-4 bg-emerald-500/20 rounded-full mb-4 inline-block"><CheckCircle2 className="text-emerald-500" size={32} /></div>
                          <p className="text-xl font-bold text-white">{data.resume.name}</p>
                          <p className="text-gray-500 text-xs mt-1">Dossier Loaded</p>
                        </div>
                    ) : (
                        <>
                          <div className="p-5 bg-blue-500/10 rounded-full mb-4 group-hover/upload:scale-110 group-hover/upload:bg-blue-500/20 transition-all"><Upload className="text-blue-500" size={30} /></div>
                          <p className="text-lg font-medium text-gray-400 group-hover/upload:text-white transition-colors">Drop PDF Resume Here</p>
                        </>
                    )}
                  </label>
                  <button onClick={() => setStep(5)} disabled={!data.resume} className="w-full bg-white text-black py-5 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-blue-500 hover:text-white transition-all disabled:opacity-50">
                    Final Calibration
                  </button>
                </motion.div>
              )}

              {/* STEP 5: HARDWARE CHECK */}
              {step === 5 && (
                <motion.div key="5" variants={variants} initial="enter" animate="center" exit="exit" className="space-y-8">
                   <div className="space-y-2">
                    <h2 className="text-3xl font-bold tracking-tight">Step 5: Hardware Sync</h2>
                    <p className="text-gray-500">Initialize biometrics for simulation.</p>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <button onClick={checkPermissions} className={`p-8 rounded-3xl border transition-all flex flex-col items-center gap-4 ${hardwareGranted.cam ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-white/10 bg-white/5 hover:bg-white/[0.08]'}`}>
                        <div className={`p-4 rounded-full ${hardwareGranted.cam ? 'bg-emerald-500/20 text-emerald-500' : 'bg-white/10 text-gray-500'}`}>
                            <Video size={24} />
                        </div>
                        <span className="text-[10px] font-black uppercase tracking-widest">{hardwareGranted.cam ? "Cam Active" : "Enable Cam"}</span>
                    </button>
                    <button onClick={checkPermissions} className={`p-8 rounded-3xl border transition-all flex flex-col items-center gap-4 ${hardwareGranted.mic ? 'border-emerald-500/50 bg-emerald-500/5' : 'border-white/10 bg-white/5 hover:bg-white/[0.08]'}`}>
                        <div className={`p-4 rounded-full ${hardwareGranted.mic ? 'bg-emerald-500/20 text-emerald-500' : 'bg-white/10 text-gray-500'}`}>
                            <Mic size={24} />
                        </div>
                        <span className="text-[10px] font-black uppercase tracking-widest">{hardwareGranted.mic ? "Mic Active" : "Enable Mic"}</span>
                    </button>
                  </div>

                  <button 
                    onClick={finalizeSetup} 
                    disabled={loading || !hardwareGranted.cam || !hardwareGranted.mic}
                    className="w-full relative group/btn overflow-hidden bg-blue-600 py-6 rounded-2xl font-black text-xl flex justify-center items-center gap-4 transition-all hover:scale-[1.02] shadow-[0_0_30px_rgba(37,99,235,0.3)] disabled:opacity-50"
                  >
                    {loading ? <Loader2 className="animate-spin" size={24} /> : <><Zap fill="white" size={20} /> INITIALIZE ENGINE</>}
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </main>

      {/* FOOTER FEATURES */}
      <footer className="max-w-[1400px] mx-auto px-8 pb-16 grid md:grid-cols-3 gap-12 border-t border-white/5 pt-16">
        {[
            { icon: ShieldCheck, t: "Strict Privacy", d: "End-to-End Dossier Encryption" },
            { icon: Clock, t: "Real-time Probes", d: "Latency < 800ms Feedback" },
            { icon: Zap, t: "8+5 Logic", d: "Dynamic Neural Pivot Active" }
        ].map((f, i) => (
            <div key={i} className="flex gap-4 items-center">
                <div className="p-3 bg-white/5 rounded-2xl text-blue-500"><f.icon size={20}/></div>
                <div>
                    <p className="text-[10px] font-black uppercase text-white tracking-widest">{f.t}</p>
                    <p className="text-sm text-gray-500">{f.d}</p>
                </div>
            </div>
        ))}
      </footer>
    </div>
  );
}