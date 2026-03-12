const DIMS = [
  { key: "market_potential",        label: "Market Potential" },
  { key: "team_strength",           label: "Team Strength" },
  { key: "product_differentiation", label: "Product Differentiation" },
  { key: "moat",                    label: "Moat" },
  { key: "traction",                label: "Traction" },
];

function barColor(v) {
  if (v >= 8) return "bg-green-500";
  if (v >= 6) return "bg-emerald-500";
  if (v >= 4) return "bg-yellow-500";
  if (v >= 2) return "bg-orange-500";
  return "bg-red-500";
}

function verdictColor(v) {
  if (v.includes("Strong Pass")) return "text-green-400";
  if (v.includes("Pass"))        return "text-emerald-400";
  if (v.includes("Lean Pass"))   return "text-yellow-400";
  if (v.includes("Lean Fail"))   return "text-orange-400";
  return "text-red-400";
}

export default function ScoreCard({ scores, finalScore, verdict }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-5">Investment Score</h3>

      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-5xl font-bold text-slate-900">{finalScore.toFixed(1)}</div>
          <div className="text-sm text-slate-500 mt-1">out of 10</div>
        </div>
        <div className={`text-2xl font-bold ${verdictColor(verdict)}`}>{verdict}</div>
      </div>

      <div className="space-y-3">
        {DIMS.map(({ key, label }) => {
          const val = scores[key] ?? 0;
          return (
            <div key={key}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600">{label}</span>
                <span className="text-slate-700 font-medium">{val.toFixed(1)}</span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div className={`h-full rounded-full transition-all duration-700 ${barColor(val)}`} style={{ width: `${val * 10}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
