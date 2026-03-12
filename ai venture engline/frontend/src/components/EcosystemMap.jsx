export default function EcosystemMap({ ecosystemMap }) {
  if (!ecosystemMap || !ecosystemMap.categories?.length) return null;

  const colors = [
    { bg: "bg-indigo-500/10", border: "border-indigo-700/40", dot: "bg-indigo-400", text: "text-indigo-300" },
    { bg: "bg-emerald-900/20", border: "border-emerald-700/40", dot: "bg-emerald-400", text: "text-emerald-300" },
    { bg: "bg-amber-900/20", border: "border-amber-700/40", dot: "bg-amber-400", text: "text-amber-300" },
    { bg: "bg-rose-900/20", border: "border-rose-700/40", dot: "bg-rose-400", text: "text-rose-300" },
    { bg: "bg-cyan-900/20", border: "border-cyan-700/40", dot: "bg-cyan-400", text: "text-cyan-300" },
  ];

  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900 mb-3">
        🗺️ {ecosystemMap.startup_name} Ecosystem Map
      </h2>
      <div className="bg-white shadow-sm border border-slate-200 rounded-xl p-5 space-y-4">
        {ecosystemMap.categories.map((cat, i) => {
          const c = colors[i % colors.length];
          return (
            <div key={i} className={`${c.bg} border ${c.border} rounded-lg p-4`}>
              <div className={`text-sm font-semibold ${c.text} mb-2 uppercase tracking-wider`}>
                {cat.name}
              </div>
              <div className="space-y-1.5">
                {cat.companies.map((company, j) => {
                  const isStartup = company.toLowerCase() === ecosystemMap.startup_name.toLowerCase();
                  const isLast = j === cat.companies.length - 1;
                  return (
                    <div key={j} className="flex items-center gap-2 text-sm">
                      <span className="text-zinc-600 font-mono text-xs w-4 text-right">
                        {isLast ? "└─" : "├─"}
                      </span>
                      <span className={`w-2 h-2 rounded-full ${isStartup ? "bg-white ring-2 ring-white/30" : c.dot}`} />
                      <span className={isStartup ? "text-slate-900 font-semibold" : "text-slate-700"}>
                        {company}
                        {isStartup && (
                          <span className="ml-2 text-xs bg-white/10 text-slate-900/70 px-1.5 py-0.5 rounded">
                            analyzing
                          </span>
                        )}
                      </span>
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
