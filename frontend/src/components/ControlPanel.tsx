import React, { useState } from "react";
import { Send, Sparkles, RefreshCw } from "lucide-react";

interface ControlPanelProps {
  onPlanTrip: (prompt: string, isDemo?: boolean) => void;
  isLoading: boolean;
  statusText: string;
  onReset: () => void;
}

export default function ControlPanel({ onPlanTrip, isLoading, statusText, onReset }: ControlPanelProps) {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isLoading) return;
    onPlanTrip(prompt);
  };

  return (
    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10 w-[90%] max-w-2xl bg-zinc-950/85 backdrop-blur-md border border-zinc-800 rounded-2xl p-4 shadow-2xl transition-all duration-300">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., I have $1200 for a weekend in London"
            className="flex-1 bg-zinc-900 border border-zinc-750 text-white placeholder-zinc-500 text-sm rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all font-sans"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !prompt.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white font-medium text-sm rounded-xl px-5 py-3 flex items-center gap-2 transition-all shadow-[0_4px_12px_rgba(59,130,246,0.3)] disabled:shadow-none"
          >
            {isLoading ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Plan</span>
          </button>
        </div>

        {/* Status bar & Dev controls */}
        <div className="flex items-center justify-between text-xs text-zinc-400 px-1 border-t border-zinc-800/60 pt-2.5">
          <div className="flex items-center gap-1.5 font-medium">
            {isLoading && <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />}
            <span className={statusText ? "text-zinc-200" : "text-zinc-500"}>
              {statusText || "Ready"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              disabled={isLoading}
              onClick={() => onPlanTrip("IDR 30,000,000 jakarta to tokyo 26-31 december 2026", true)}
              className="flex items-center gap-1 text-zinc-400 hover:text-amber-400 font-medium transition-colors cursor-pointer disabled:opacity-50"
              title="Run 2s Map Choreography Demo"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Run Demo</span>
            </button>
            <button
              type="button"
              onClick={onReset}
              className="flex items-center gap-1 text-zinc-400 hover:text-rose-400 font-medium transition-colors cursor-pointer"
              title="Reset session state"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Reset</span>
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
