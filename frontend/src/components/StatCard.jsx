import React from "react";

export default function StatCard({
  icon,
  label,
  value,
  hint,
  tone = "cyan", // cyan | blue | violet
}) {
  const toneMap = {
    cyan: {
      ring: "hover:border-cyan-400/30",
      iconWrap: "bg-cyan-500/10 text-cyan-300 border-cyan-400/15",
      glow: "shadow-[0_0_30px_rgba(34,211,238,0.12)]",
    },
    blue: {
      ring: "hover:border-blue-400/30",
      iconWrap: "bg-blue-500/10 text-blue-300 border-blue-400/15",
      glow: "shadow-[0_0_30px_rgba(96,165,250,0.12)]",
    },
    violet: {
      ring: "hover:border-violet-400/30",
      iconWrap: "bg-violet-500/10 text-violet-300 border-violet-400/15",
      glow: "shadow-[0_0_30px_rgba(167,139,250,0.12)]",
    },
  };

  const t = toneMap[tone] ?? toneMap.cyan;

  return (
    <div
      className={[
        "relative overflow-hidden rounded-[2.5rem] border border-white/10 bg-white/[0.03] p-7 backdrop-blur-2xl transition",
        t.ring,
      ].join(" ")}
    >
      <div className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity">
        <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-white/5 blur-2xl" />
      </div>

      <div className="relative flex items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div
            className={[
              "rounded-2xl border p-3",
              t.iconWrap,
              t.glow,
            ].join(" ")}
          >
            {icon}
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.28em] text-slate-400">
              {label}
            </p>
            <p className="mt-1 text-3xl font-black tracking-tight text-white italic">
              {value}
            </p>
          </div>
        </div>

        {hint ? (
          <p className="max-w-[12rem] text-right text-[11px] font-semibold text-slate-400/80 leading-snug">
            {hint}
          </p>
        ) : null}
      </div>
    </div>
  );
}

