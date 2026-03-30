import React from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, BarChart3, TrendingUp } from 'lucide-react';

const StatBox = ({ label, score, color }) => (
  <div className="bg-white/5 p-4 rounded-2xl border border-white/10 text-center">
    <p className="text-gray-400 text-sm mb-1">{label}</p>
    <h4 className={`text-3xl font-black ${color}`}>{score}%</h4>
  </div>
);

export default function Evaluation({ report }) {
  // Mock Report Data (Backend se aayega)
  const data = report || {
    overall: 65,
    grammar: 7.2,
    fluency: 6.5,
    feedback: "Your technical knowledge is okay, but you lack confidence. Your explanation of 'Redux' was messy. Stop using 'ummm' and 'like' so much.",
    improvements: ["Work on voice modulation", "Deep dive into React Lifecycle hooks"]
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <header className="flex items-center gap-4 mb-10">
          <div className="p-3 bg-red-600/20 rounded-full text-red-500">
            <AlertCircle size={32} />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Brutally Honest Review</h1>
            <p className="text-gray-400">AI has analyzed your performance. No sugarcoating.</p>
          </div>
        </header>

        <div className="grid md:grid-cols-3 gap-6 mb-8">
          <StatBox label="Overall Score" score={data.overall} color="text-blue-500" />
          <StatBox label="Grammar Level" score={data.grammar * 10} color="text-green-500" />
          <StatBox label="Fluency" score={data.fluency * 10} color="text-yellow-500" />
        </div>

        <div className="bg-white/5 border border-white/10 p-8 rounded-3xl mb-8">
          <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
            <TrendingUp className="text-blue-500" /> AI Feedback
          </h3>
          <p className="text-gray-300 italic leading-relaxed text-lg">"{data.feedback}"</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="bg-green-500/10 border border-green-500/20 p-6 rounded-2xl">
            <h4 className="font-bold text-green-400 mb-4 flex items-center gap-2">
                <CheckCircle size={20}/> Things You Did Well
            </h4>
            <ul className="list-disc list-inside text-gray-400 space-y-2">
                <li>Strong understanding of Database schemas.</li>
                <li>Good eye contact with the camera.</li>
            </ul>
          </div>
          <button 
            onClick={() => window.location.href = "/"}
            className="h-full bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl flex items-center justify-center transition-all"
          >
            Go to Dashboard & Check Progress
          </button>
        </div>
      </div>
    </div>
  );
}