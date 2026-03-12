import { motion } from "framer-motion";
import { AlertCircle, CheckCircle, AlertTriangle, FileText } from "lucide-react";

export default function SlideFeedback({ slideFeedback }) {
  if (!slideFeedback || slideFeedback.length === 0) return null;

  return (
    <div className="mb-10">
      <h2 className="text-2xl font-bold text-slate-900 mb-6 border-l-4 border-indigo-500 pl-4">
        Investor Attention Heatmap
      </h2>
      
      {/* Visual heatmap grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-8">
        {slideFeedback.map((slide) => (
          <SlideCard key={slide.slide_number} slide={slide} />
        ))}
      </div>

      {/* Detailed feedback */}
      <div className="space-y-4">
        {slideFeedback
          .filter(s => s.severity !== "low")
          .sort((a, b) => severityRank(b.severity) - severityRank(a.severity))
          .map((slide) => (
            <SlideDetailCard key={slide.slide_number} slide={slide} />
          ))}
      </div>
    </div>
  );
}

function SlideCard({ slide }) {
  const severityColors = {
    critical: "border-rose-400 bg-rose-50",
    high: "border-orange-400 bg-orange-50",
    medium: "border-amber-400 bg-amber-50",
    low: "border-emerald-400 bg-emerald-50",
  };

  const severityIcons = {
    critical: <AlertCircle className="w-4 h-4 text-rose-600" />,
    high: <AlertTriangle className="w-4 h-4 text-orange-600" />,
    medium: <AlertTriangle className="w-4 h-4 text-amber-600" />,
    low: <CheckCircle className="w-4 h-4 text-emerald-600" />,
  };

  const severityLabels = {
    critical: "Critical Issue",
    high: "Major Concern",
    medium: "Needs Improvement",
    low: "Strong",
  };

  const severityTextColors = {
    critical: "text-rose-700",
    high: "text-orange-700",
    medium: "text-amber-700",
    low: "text-emerald-700",
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.03 }}
      className={`relative bg-white border-2 rounded-xl p-4 cursor-pointer transition-all shadow-sm hover:shadow-md ${
        severityColors[slide.severity] || severityColors.low
      }`}
    >
      <div className="flex items-center gap-2 mb-3">
        <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-white font-bold text-sm">
          {slide.slide_number}
        </div>
        <div className="flex-1 text-xs font-bold text-slate-500 uppercase tracking-wider">
          {slide.slide_type.replace(/_/g, " ")}
        </div>
        {severityIcons[slide.severity]}
      </div>
      <div className="text-sm font-semibold text-slate-900 line-clamp-2 mb-2">
        {slide.slide_title}
      </div>
      <div className={`text-xs font-bold ${severityTextColors[slide.severity]}`}>
        {severityLabels[slide.severity]}
      </div>
    </motion.div>
  );
}

function SlideDetailCard({ slide }) {
  const severityColors = {
    critical: "border-rose-500/30 bg-rose-500/5",
    high: "border-orange-500/30 bg-orange-500/5",
    medium: "border-amber-500/30 bg-amber-500/5",
  };

  const severityBadges = {
    critical: "bg-rose-500/10 text-rose-500 border-rose-500/20",
    high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    medium: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-2xl p-6 ${severityColors[slide.severity] || ""}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-700 font-bold">
            {slide.slide_number}
          </div>
          <div>
            <div className="text-xs font-bold text-slate-600 uppercase tracking-wider">
              {slide.slide_type.replace(/_/g, " ")}
            </div>
            <div className="text-lg font-bold text-slate-900">{slide.slide_title}</div>
          </div>
        </div>
        <span className={`px-3 py-1 rounded-lg text-xs font-bold border ${
          severityBadges[slide.severity] || "bg-slate-100 text-slate-600 border-slate-300"
        }`}>
          {slide.severity.toUpperCase()}
        </span>
      </div>

      {slide.problem && (
        <div className="mb-4 p-4 bg-white rounded-xl border border-slate-200">
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">
            Problem Detected
          </div>
          <div className="text-slate-900 font-medium">{slide.problem}</div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="p-4 bg-white rounded-xl border border-slate-200">
          <div className="text-xs font-bold text-slate-600 uppercase tracking-wider mb-2">
            Investor Reaction
          </div>
          <div className="text-slate-700 text-sm">{slide.investor_reaction}</div>
        </div>

        <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200">
          <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider mb-2">
            Fix Suggestion
          </div>
          <div className="text-emerald-900 text-sm font-medium">{slide.fix_suggestion}</div>
        </div>
      </div>
    </motion.div>
  );
}

function severityRank(severity) {
  const ranks = { critical: 4, high: 3, medium: 2, low: 1 };
  return ranks[severity] || 0;
}
