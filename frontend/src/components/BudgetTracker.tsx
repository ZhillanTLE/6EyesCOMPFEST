import React from "react";

interface BudgetTrackerProps {
  totalBudget: number | null;
  remainingBudget: number | null;
  currency?: string;
  currencySymbol?: string;
}

export default function BudgetTracker({ totalBudget, remainingBudget, currency = "USD", currencySymbol = "$" }: BudgetTrackerProps) {
  const isStarted = totalBudget !== null;
  const displayTotal = totalBudget ?? 0;
  const displayRemaining = remainingBudget ?? displayTotal;
  
  // Calculate percentage remaining for the visual progress bar
  const percentRemaining = isStarted && displayTotal > 0 
    ? Math.max(0, Math.min(100, (displayRemaining / displayTotal) * 100))
    : 100;

  // Determine indicator colors based on budget levels
  let progressColor = "bg-emerald-500";
  if (percentRemaining < 25) {
    progressColor = "bg-rose-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]";
  } else if (percentRemaining < 60) {
    progressColor = "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]";
  } else {
    progressColor = "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]";
  }

  const formatPrice = (val: number) => {
    if (currency === "IDR") {
      return `Rp ${val.toLocaleString("id-ID", { maximumFractionDigits: 0 })}`;
    }
    if (currency === "JPY") {
      return `¥${val.toLocaleString("ja-JP", { maximumFractionDigits: 0 })}`;
    }
    if (currency === "CNY") {
      return `¥${val.toLocaleString("zh-CN", { maximumFractionDigits: 0 })}`;
    }
    if (currency === "EUR") {
      return `€${val.toLocaleString("de-DE", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
    }
    return `${currencySymbol}${val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="absolute top-6 left-6 z-10 w-80 bg-zinc-950/80 backdrop-blur-md border border-zinc-800 rounded-xl p-5 shadow-2xl transition-all duration-300">
      <div className="text-zinc-500 text-xs font-semibold uppercase tracking-widest mb-1">
        Budget Tracker
      </div>
      
      {!isStarted ? (
        <div className="text-zinc-400 text-sm">
          Enter a prompt below to start tracking your travel budget.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-baseline">
            <div>
              <div className="text-zinc-400 text-[10px] uppercase font-bold tracking-wider">
                Remaining
              </div>
              <div className="text-3xl font-mono font-bold tracking-tight text-white transition-all duration-500">
                {formatPrice(displayRemaining)}
              </div>
            </div>
            <div className="text-right">
              <div className="text-zinc-500 text-[10px] uppercase font-bold tracking-wider">
                Total
              </div>
              <div className="text-lg font-mono font-medium text-zinc-300">
                {formatPrice(displayTotal)}
              </div>
            </div>
          </div>

          {/* Visual Budget Bar */}
          <div className="space-y-1">
            <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden">
              <div 
                className={`h-full ${progressColor} transition-all duration-500`}
                style={{ width: `${percentRemaining}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] font-mono text-zinc-500 font-semibold">
              <span>0%</span>
              <span>{percentRemaining.toFixed(0)}% left</span>
              <span>100%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
