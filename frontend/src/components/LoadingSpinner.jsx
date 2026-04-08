import React from "react";

export default function LoadingSpinner({ label = "Loading" }) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-3xl border border-white/10 bg-white/[0.03] px-6 py-5 backdrop-blur-2xl">
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-cyan-400/30 border-t-cyan-400" />
      <p className="text-xs font-black uppercase tracking-[0.25em] text-slate-300">
        {label}
      </p>
    </div>
  );
}

