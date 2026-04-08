import React from "react";

function clamp01(n) {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(100, n));
}

export default function SkillBars({ skills = [] }) {
  return (
    <div className="rounded-[2.5rem] border border-white/10 bg-white/[0.03] p-8 backdrop-blur-2xl">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-black tracking-[0.3em] text-blue-300/80 uppercase">
            Skill matrix
          </p>
          <p className="mt-2 text-xl font-black text-white tracking-tight">
            Neural breakdown
          </p>
        </div>
        <p className="text-[11px] font-bold text-slate-400">
          Premium bars • 0–100
        </p>
      </div>

      <div className="mt-8 space-y-5">
        {skills.map((s, i) => {
          const v = clamp01(Number(s?.A ?? 0));
          return (
            <div key={`${s?.subject ?? "skill"}-${i}`} className="space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-black uppercase tracking-widest text-slate-300">
                  {s?.subject ?? "Skill"}
                </p>
                <p className="text-xs font-black font-mono text-slate-200">
                  {v}%
                </p>
              </div>

              <div className="h-3 w-full rounded-full bg-black/40 border border-white/5 p-0.5 overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-violet-500 shadow-[0_0_18px_rgba(99,102,241,0.25)] transition-[width] duration-700 ease-out"
                  style={{ width: `${v}%` }}
                />
              </div>
            </div>
          );
        })}

        {!skills?.length ? (
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4 text-xs font-semibold text-slate-400">
            No skill data yet.
          </div>
        ) : null}
      </div>
    </div>
  );
}

