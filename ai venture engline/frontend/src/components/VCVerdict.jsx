import { motion } from "framer-motion";
import { Scale, AlertTriangle, TrendingUp } from "lucide-react";

export default function VCVerdict({ memo }) {
  if (!memo) return null;

  // Determine decision based on verdict
  const isPass = ["Strong Pass", "Pass", "Lean Pass"].includes(memo.verdict);
  const decision = isPass ? "PASS" : "FAIL";
  
  // Extract top 3 concerns from memo
  const concerns = memo.top_investor_concerns?.slice(0, 3) || [];
  
  // Extract potential catalysts from bull case
  const catalysts = extractCatalysts(memo);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700 rounded-3xl p-8 mb-10 relative overflow-hidden shadow-2xl"
    >
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl" />
      
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
            <Scale className="w-6 h-6 text-indigo-400" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">Instant VC Verdict</div>
            <div className="text-sm text-slate-500">Investment Committee Summary</div>
          </div>
        </div>

        {/* Decision */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-2">
            <span className="text-slate-400 font-semibold">Decision:</span>
            <span className={`text-3xl font-black tracking-tight ${
              isPass ? "text-emerald-400" : "text-rose-400"
            }`}>
              {decision}
            </span>
            <span className={`px-3 py-1 rounded-lg text-xs font-bold border ${
              isPass 
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
            }`}>
              {memo.verdict}
            </span>
          </div>
          <div className="text-slate-300 text-sm">
            Final Score: <span className="font-bold text-white">{memo.final_score.toFixed(1)}</span> / 10
          </div>
        </div>

        {/* Why investors hesitate */}
        {concerns.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
              <h3 className="text-lg font-bold text-slate-200">Why investors hesitate:</h3>
            </div>
            <div className="space-y-3">
              {concerns.map((concern, i) => (
                <div key={i} className="flex items-start gap-3 bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                  <div className="w-6 h-6 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center flex-shrink-0 text-rose-400 font-bold text-xs">
                    {i + 1}
                  </div>
                  <span className="text-slate-300 text-sm leading-relaxed">{concern}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What could change this */}
        {catalysts.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <h3 className="text-lg font-bold text-slate-200">What could change this:</h3>
            </div>
            <div className="space-y-3">
              {catalysts.map((catalyst, i) => (
                <div key={i} className="flex items-start gap-3 bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
                  <div className="w-6 h-6 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center flex-shrink-0 text-emerald-400 font-bold text-xs">
                    ✓
                  </div>
                  <span className="text-slate-300 text-sm leading-relaxed">{catalyst}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}

// Extract potential catalysts from bull case and rebuttal
function extractCatalysts(memo) {
  const catalysts = [];
  
  // Look for specific improvements mentioned in bull rebuttal
  const rebuttalText = memo.bull_rebuttal || "";
  
  // Common catalyst patterns
  const patterns = [
    /reduce CAC/i,
    /enterprise contracts/i,
    /product-led growth/i,
    /proprietary.*moat/i,
    /network effects/i,
    /proven.*economics/i,
  ];
  
  // Extract from bull rebuttal
  if (rebuttalText.includes("CAC") || rebuttalText.includes("customer acquisition")) {
    catalysts.push("Reduce CAC via product-led growth or viral distribution");
  }
  
  if (rebuttalText.includes("enterprise") || rebuttalText.includes("B2B")) {
    catalysts.push("Show enterprise contracts or pilot programs with Fortune 500");
  }
  
  if (rebuttalText.includes("moat") || rebuttalText.includes("defensib") || rebuttalText.includes("proprietary")) {
    catalysts.push("Demonstrate proprietary dataset moat or network effects");
  }
  
  // Fallback generic catalysts if none found
  if (catalysts.length === 0) {
    catalysts.push("Prove unit economics with CAC payback < 12 months");
    catalysts.push("Show 3x YoY growth with improving margins");
    catalysts.push("Build defensible moat through data or network effects");
  }
  
  return catalysts.slice(0, 3);
}
