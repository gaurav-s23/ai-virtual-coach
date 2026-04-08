import React from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

export default function ErrorState({
  title = "Backend unavailable",
  message = "We couldn't reach the API. Check if FastAPI is running on port 8000.",
  onRetry,
}) {
  return (
    <div className="rounded-3xl border border-red-500/20 bg-red-500/5 p-6 backdrop-blur-2xl">
      <div className="flex items-start gap-4">
        <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-3 text-red-300">
          <AlertTriangle size={18} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-black text-white">{title}</p>
          <p className="mt-1 text-xs font-medium text-red-100/70">{message}</p>
          {onRetry ? (
            <button
              onClick={onRetry}
              className="mt-4 inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-2 text-xs font-black uppercase tracking-widest text-white hover:bg-white/[0.1] transition"
            >
              <RefreshCcw size={14} />
              Retry
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

