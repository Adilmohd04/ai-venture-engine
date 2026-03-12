const SEV_STYLES = {
  critical: { bg: "bg-red-900/30",    border: "border-red-700",    text: "text-red-400",    badge: "bg-red-500" },
  high:     { bg: "bg-orange-900/30",  border: "border-orange-700",  text: "text-orange-400",  badge: "bg-orange-500" },
  medium:   { bg: "bg-yellow-900/30",  border: "border-yellow-700",  text: "text-yellow-400",  badge: "bg-yellow-500" },
  low:      { bg: "bg-green-900/30",   border: "border-green-700",   text: "text-green-400",   badge: "bg-green-500" },
};

const CAT_LABELS = {
  market_saturation:       "Market Saturation",
  weak_moat:               "Weak Moat",
  founder_domain_mismatch: "Founder Mismatch",
  unclear_business_model:  "Unclear Biz Model",
  regulatory_risk:         "Regulatory Risk",
  scaling_challenges:      "Scaling Challenges",
  platform_dependency:     "Platform Dependency",
  ai_commoditization:      "AI Commoditization",
  low_willingness_to_pay:  "Low Willingness to Pay",
  concentration_risk:      "Concentration Risk",
};

export default function RiskRadar({ risks }) {
  const signals = risks?.signals || [];
  if (!signals.length) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center gap-2">
        ⚠️ Risk Signals
        <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full">{signals.length}</span>
      </h3>
      <div className="space-y-3">
        {signals.map((s, i) => {
          const sty = SEV_STYLES[s.severity] || SEV_STYLES.medium;
          return (
            <div key={i} className={`${sty.bg} border ${sty.border} rounded-lg p-4`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-bold uppercase px-2 py-0.5 rounded ${sty.badge} text-slate-900`}>{s.severity}</span>
                <span className={`text-sm font-medium ${sty.text}`}>{CAT_LABELS[s.category] || s.category}</span>
              </div>
              <p className="text-slate-700 text-sm">{s.description}</p>
              {s.evidence && <p className="text-slate-9000 text-xs mt-1 italic">{s.evidence}</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
