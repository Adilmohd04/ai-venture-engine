const VERDICT_STYLES = {
  outperforming:   { bg: "bg-green-900/30",  text: "text-green-400",  border: "border-green-700/40", icon: "🚀" },
  "above average": { bg: "bg-emerald-900/30", text: "text-emerald-400", border: "border-emerald-700/40", icon: "📈" },
  "at par":        { bg: "bg-yellow-900/30",  text: "text-yellow-400",  border: "border-yellow-700/40", icon: "➡️" },
  "below average": { bg: "bg-orange-900/30",  text: "text-orange-400",  border: "border-orange-700/40", icon: "📉" },
  underperforming: { bg: "bg-red-900/30",     text: "text-red-400",     border: "border-red-700/40",    icon: "⚠️" },
};

function getVerdictStyle(verdict) {
  if (!verdict) return VERDICT_STYLES["at par"];
  return VERDICT_STYLES[verdict.toLowerCase()] || VERDICT_STYLES["at par"];
}

export default function BenchmarkTable({ benchmark }) {
  if (!benchmark?.categories?.length) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-2 flex items-center gap-2">
        📊 {benchmark.startup_name} vs Competitors
      </h3>

      {/* Overall position summary */}
      {benchmark.overall_position && (
        <p className="text-slate-600 text-sm mb-5 italic border-l-2 border-indigo-500 pl-3">
          {benchmark.overall_position}
        </p>
      )}

      <div className="space-y-6">
        {benchmark.categories.map((cat, ci) => {
          const vs = getVerdictStyle(cat.startup_verdict);
          return (
            <div key={ci}>
              {/* Category header with verdict + percentile */}
              <div className="flex items-center justify-between mb-2">
                <div className="text-sm font-medium text-indigo-400 uppercase tracking-wider">
                  {cat.metric_name}
                </div>
                <div className="flex items-center gap-2">
                  {cat.startup_percentile && (
                    <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                      {cat.startup_percentile}
                    </span>
                  )}
                  {cat.startup_verdict && (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded border ${vs.bg} ${vs.text} ${vs.border}`}>
                      {vs.icon} {cat.startup_verdict}
                    </span>
                  )}
                </div>
              </div>

              {/* Entries */}
              <div className="space-y-1.5">
                {cat.entries.map((entry, ei) => {
                  const isStartup = entry.is_startup || entry.entity.toLowerCase() === benchmark.startup_name.toLowerCase();
                  const isMedian = entry.is_median || entry.entity.toLowerCase().includes("median") || entry.entity.toLowerCase().includes("sector");
                  return (
                    <div
                      key={ei}
                      className={`flex items-center justify-between rounded-lg px-4 py-2.5 ${
                        isStartup
                          ? "bg-indigo-900/30 border border-indigo-700/40"
                          : isMedian
                          ? "bg-slate-100/80 border border-slate-300/40 border-dashed"
                          : "bg-slate-100/40"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {isStartup && <span className="text-indigo-400 text-xs">★</span>}
                        {isMedian && <span className="text-slate-9000 text-xs">◆</span>}
                        <span className={`text-sm ${
                          isStartup ? "text-indigo-300 font-semibold"
                          : isMedian ? "text-slate-600 italic"
                          : "text-slate-700"
                        }`}>
                          {entry.entity}
                        </span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-sm font-mono font-bold ${
                          isStartup ? "text-indigo-300" : "text-zinc-200"
                        }`}>
                          {entry.value}
                        </span>
                        <span className="text-xs text-zinc-600 hidden sm:inline max-w-[120px] truncate">
                          {entry.source}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
