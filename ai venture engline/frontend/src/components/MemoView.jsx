import ScoreCard from "./ScoreCard";
import RiskRadar from "./RiskRadar";
import EcosystemMap from "./EcosystemMap";
import BenchmarkTable from "./BenchmarkTable";
import SlideFeedback from "./SlideFeedback";
import VCVerdict from "./VCVerdict";
import { motion } from "framer-motion";
import { Download, AlertCircle, CheckCircle, Info, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function MemoView({ memo, onDownloadPdf }) {
  if (!memo) return null;

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
  };

  return (
    <motion.div variants={containerVariants} initial="hidden" animate="show" className="max-w-5xl mx-auto py-12 space-y-10" id="memo-content">
      {/* Header */}
      <motion.div variants={itemVariants} className="text-center border-b border-slate-200 pb-8 relative">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-indigo-500 rounded-b-full blur-sm opacity-50" />
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-indigo-500/10 text-indigo-400 text-xs font-semibold rounded-full border border-indigo-500/20 mb-4">
           <FileText className="w-3.5 h-3.5" /> CONFIDENTIAL
        </div>
        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight">Investment Memo</h1>
        <p className="text-slate-9000 mt-3 font-medium text-lg">Generated {new Date(memo.created_at).toLocaleDateString()}</p>
      </motion.div>

      {/* Instant VC Verdict - NEW */}
      <motion.div variants={itemVariants}>
        <VCVerdict memo={memo} />
      </motion.div>

      {/* Investor Readiness Score */}
      {memo.investor_readiness && (
        <motion.div variants={itemVariants}>
          <InvestorReadinessCard readiness={memo.investor_readiness} />
        </motion.div>
      )}

      {/* Deal Breakers - Top 3 Critical Issues */}
      {memo.deal_breakers && memo.deal_breakers.length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="🚨 Deal Breakers">
            <div className="bg-gradient-to-br from-rose-50 to-red-50 border-2 border-rose-300 rounded-2xl p-6">
              <p className="text-slate-700 text-sm mb-6 font-medium">
                These are the top {memo.deal_breakers.length} critical issues that could prevent investment:
              </p>
              <div className="space-y-4">
                {memo.deal_breakers.map((breaker, i) => (
                  <div key={i} className="bg-white border-2 border-rose-200 rounded-xl p-5 hover:shadow-md transition-shadow">
                    <div className="flex items-start gap-4 mb-3">
                      <div className="w-8 h-8 rounded-full bg-rose-500 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                        {breaker.rank || i + 1}
                      </div>
                      <div className="flex-1">
                        <h4 className="text-slate-900 font-bold text-lg mb-1">{breaker.issue}</h4>
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-bold ${
                          breaker.severity === "critical" 
                            ? "bg-rose-100 text-rose-700 border border-rose-300" 
                            : breaker.severity === "high"
                            ? "bg-orange-100 text-orange-700 border border-orange-300"
                            : "bg-amber-100 text-amber-700 border border-amber-300"
                        }`}>
                          {breaker.severity?.toUpperCase() || "HIGH"} SEVERITY
                        </span>
                      </div>
                    </div>
                    <p className="text-slate-700 text-sm leading-relaxed mb-3 pl-12">
                      {breaker.explanation}
                    </p>
                    <div className="pl-12 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                      <div className="text-xs font-bold text-emerald-700 uppercase tracking-wide mb-1">
                        💡 How to fix:
                      </div>
                      <p className="text-slate-700 text-sm leading-relaxed">
                        {breaker.recommendation}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Section>
        </motion.div>
      )}

      {/* Investor Questions - Tough Questions VCs Will Ask */}
      {memo.investor_questions && memo.investor_questions.length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="❓ Tough Questions VCs Will Ask">
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border-2 border-indigo-300 rounded-2xl p-6">
              <p className="text-slate-700 text-sm mb-6 font-medium">
                Prepare answers to these {memo.investor_questions.length} critical questions before your pitch:
              </p>
              <div className="space-y-4">
                {memo.investor_questions.map((question, i) => (
                  <div key={i} className="bg-white border-2 border-indigo-200 rounded-xl p-5 hover:shadow-md transition-shadow">
                    <div className="flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-indigo-500 text-white flex items-center justify-center font-bold text-sm flex-shrink-0">
                        {i + 1}
                      </div>
                      <div className="flex-1">
                        <p className="text-slate-900 font-semibold text-base leading-relaxed">
                          {question}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-6 bg-white border border-indigo-200 rounded-xl p-4">
                <p className="text-slate-600 text-sm flex items-start gap-2">
                  <Info className="w-4 h-4 shrink-0 mt-0.5 text-indigo-500" />
                  <span>
                    <strong className="text-slate-900">Pro tip:</strong> Practice answering these questions with data-backed responses. VCs expect specific metrics, not vague promises.
                  </span>
                </p>
              </div>
            </div>
          </Section>
        </motion.div>
      )}

      {/* Slide-by-Slide Feedback */}
      {memo.slide_feedback && (
        <motion.div variants={itemVariants}>
          <SlideFeedback slideFeedback={memo.slide_feedback} />
        </motion.div>
      )}

      {/* Startup Overview */}
      <motion.div variants={itemVariants}>
        <Section title="Startup Overview">
          <div className="bg-white shadow-sm border border-slate-200 rounded-2xl p-6 text-slate-700 leading-relaxed">
            {memo.startup_overview}
          </div>
        </Section>
      </motion.div>

      {/* Market Size */}
      <motion.div variants={itemVariants}>
        <Section title="Market Opportunity">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[["TAM", memo.market_size?.tam, "Total Addressable Market"], ["SAM", memo.market_size?.sam, "Serviceable Addressable Market"], ["SOM", memo.market_size?.som, "Serviceable Obtainable Market"]].map(([label, val, desc]) => (
              <div key={label} className="bg-white shadow-sm border border-slate-200 rounded-2xl p-6 text-center hover:bg-slate-50 transition-colors">
                <div className="text-sm font-bold text-slate-9000 tracking-widest">{label}</div>
                <div className="text-3xl font-extrabold text-slate-900 mt-2 mb-1 drop-shadow-sm">{formatMarketNum(val)}</div>
                <div className="text-xs text-zinc-600">{desc}</div>
              </div>
            ))}
          </div>
        </Section>
      </motion.div>

      {/* Competitors */}
      {memo.competitor_landscape?.length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="Competitor Landscape">
            <div className="grid gap-3">
              {memo.competitor_landscape.map((c, i) => (
                <div key={i} className="bg-white shadow-sm backdrop-blur-sm border border-slate-200 rounded-xl p-5 flex justify-between items-center group hover:border-indigo-500/30 transition-all">
                  <div>
                    <span className="text-slate-900 font-bold text-lg">{c.name}</span>
                    <p className="text-slate-600 text-sm mt-1">{c.description}</p>
                  </div>
                  {c.funding && (
                    <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-semibold whitespace-nowrap ml-4">
                      {c.funding}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </Section>
        </motion.div>
      )}

      {/* Bull / Bear Cases */}
      <motion.div variants={itemVariants} className="grid md:grid-cols-2 gap-6">
        <CaseSection title="Bull Case" icon="📈" color="emerald" text={memo.bull_case} />
        <CaseSection title="Bear Case" icon="📉" color="rose" text={memo.bear_case} />
      </motion.div>
      <motion.div variants={itemVariants} className="grid md:grid-cols-2 gap-6">
        <CaseSection title="Bull Rebuttal" icon="🛡️" color="indigo" text={memo.bull_rebuttal} />
        <CaseSection title="Bear Rebuttal" icon="⚠️" color="amber" text={memo.bear_rebuttal} />
      </motion.div>

      {/* Ecosystem Map */}
      {memo.ecosystem_map && (
        <motion.div variants={itemVariants}>
          <EcosystemMap ecosystemMap={memo.ecosystem_map} />
        </motion.div>
      )}

      {/* Market Benchmarking */}
      {memo.market_benchmark && (
        <motion.div variants={itemVariants}>
          <BenchmarkTable benchmark={memo.market_benchmark} />
        </motion.div>
      )}

      {/* Key Metrics with Citations */}
      {memo.structured_extraction?.key_metrics?.length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="Key Metrics & Citations">
            <div className="bg-white shadow-sm border border-slate-200 rounded-2xl overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-white shadow-sm">
                    <th className="text-left font-semibold text-slate-600 py-4 px-6">Metric / Claim</th>
                    <th className="text-left font-semibold text-slate-600 py-4 px-6">Source</th>
                    <th className="text-center font-semibold text-slate-600 py-4 px-6 w-24">Page</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {memo.structured_extraction.key_metrics.map((m, i) => {
                    // Clean source: remove "Page X" or "Pitch Deck, Page X" from source since page has its own column
                    const cleanSource = (m.source || "").replace(/,?\s*Page\s*\d+/gi, "").trim() || "Pitch Deck";
                    return (
                      <tr key={i} className="hover:bg-slate-50 transition-colors">
                        <td className="text-slate-700 py-4 px-6 font-medium">{m.text}</td>
                        <td className="text-slate-600 py-4 px-6">{cleanSource}</td>
                        <td className="text-slate-600 py-4 px-6 text-center">
                          <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 text-xs font-mono font-bold">{m.page || "—"}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Section>
        </motion.div>
      )}

      {/* Claim Verifications */}
      {memo.claim_verifications?.length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="Claim Verification">
            <div className="grid gap-3">
              {memo.claim_verifications.map((cv, i) => (
                <div key={i} className="bg-white shadow-sm border border-slate-200 rounded-xl p-5 hover:bg-slate-50 transition-colors">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <span className="text-slate-900 font-medium">{cv.claim}</span>
                    <ConfidenceBadge level={cv.confidence} />
                  </div>
                  <p className="text-slate-600 text-sm flex items-start gap-2">
                     <Info className="w-4 h-4 shrink-0 mt-0.5 text-slate-500" /> {cv.reasoning.replace(/external claim/gi, "Industry data point").replace(/without clear source/gi, "— verify with primary source").replace(/with cited source/gi, "— source referenced")}
                  </p>
                </div>
              ))}
            </div>
          </Section>
        </motion.div>
      )}

      {/* Missing Information */}
      {memo.missing_info?.length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="Missing Information">
            <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
              <div className="space-y-3">
                {memo.missing_info.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm">
                    <div className="mt-1 w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
                    <span className="text-slate-600 leading-relaxed">{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </Section>
        </motion.div>
      )}

      {/* Confidence Scores */}
      {memo.confidence_scores && Object.keys(memo.confidence_scores).length > 0 && (
        <motion.div variants={itemVariants}>
          <Section title="Analysis Confidence">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(memo.confidence_scores).map(([dim, level]) => (
                <div key={dim} className="bg-white shadow-sm border border-slate-200 rounded-xl p-4 flex flex-col items-center justify-center text-center">
                  <div className="text-xs font-bold text-slate-9000 uppercase tracking-widest mb-3">
                    {dim.replace(/_/g, " ")}
                  </div>
                  <ConfidenceBadge level={level} className="w-full justify-center py-1.5" />
                </div>
              ))}
            </div>
          </Section>
        </motion.div>
      )}

      {/* Score + Risk side by side */}
      <motion.div variants={itemVariants} className="grid md:grid-cols-2 gap-6">
        <ScoreCard scores={memo.score_breakdown} finalScore={memo.final_score} verdict={memo.verdict} />
        <RiskRadar risks={memo.risk_signals} />
      </motion.div>

      {/* Judge Reasoning */}
      <motion.div variants={itemVariants}>
        <Section title="Final Judge Reasoning">
          <div className="relative bg-gradient-to-br from-indigo-500/10 to-purple-900/10 border border-indigo-500/20 rounded-2xl p-8 backdrop-blur-sm">
            <div className="absolute top-4 right-4 opacity-10">
              <FileText className="w-24 h-24 text-indigo-500" />
            </div>
            <p className="text-slate-700 whitespace-pre-wrap leading-relaxed relative z-10 text-lg">
              {memo.judge_reasoning}
            </p>
          </div>
        </Section>
      </motion.div>

      {/* Download */}
      <motion.div variants={itemVariants} className="flex justify-center pt-10 pb-20">
        <button
          onClick={onDownloadPdf}
          className="group flex items-center gap-3 px-8 py-4 bg-indigo-50 text-indigo-700 hover:bg-indigo-50 rounded-xl font-bold transition-all shadow-xl shadow-white/5 active:scale-95"
        >
          <Download className="w-5 h-5 group-hover:-translate-y-1 transition-transform" />
          Download Executive Summary PDF
        </button>
      </motion.div>
    </motion.div>
  );
}

function formatMarketNum(val) {
  if (!val) return "N/A";
  if (typeof val === "string" && /[BMKbmk$]/.test(val)) return val;
  const num = typeof val === "string" ? parseFloat(val.replace(/[,$]/g, "")) : val;
  if (isNaN(num)) return val;
  if (num >= 1e9) return `$${(num / 1e9).toFixed(num % 1e9 === 0 ? 0 : 1)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(num % 1e6 === 0 ? 0 : 1)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(0)}K`;
  return `$${num.toLocaleString()}`;
}

function Section({ title, children }) {
  return (
    <div className="mb-10">
      <h2 className="text-2xl font-bold text-slate-900 mb-6 border-l-4 border-indigo-500 pl-4">{title}</h2>
      {children}
    </div>
  );
}

function CaseSection({ title, icon, color, text }) {
  const colorMap = {
    emerald: "bg-emerald-50 border-emerald-200",
    rose: "bg-rose-50 border-rose-200",
    indigo: "bg-indigo-50 border-indigo-200",
    amber: "bg-amber-50 border-amber-200"
  };
  const style = colorMap[color] || colorMap.indigo;
  
  return (
    <div className={`${style} border rounded-2xl p-6 relative overflow-hidden group`}>
      <div className={`absolute -right-4 -top-4 text-8xl opacity-5 group-hover:scale-110 transition-transform duration-500`}>{icon}</div>
      <h3 className="font-bold text-lg mb-4 flex items-center gap-2 relative z-10 text-slate-900">
        <span className="text-xl">{icon}</span> {title}
      </h3>
      <div className="text-slate-700 text-sm max-h-60 overflow-y-auto pr-2 relative z-10 custom-scrollbar leading-relaxed prose prose-sm max-w-none prose-slate prose-p:my-2 prose-headings:my-3 prose-headings:text-slate-900 prose-strong:text-slate-900 prose-strong:font-semibold prose-li:my-1">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text || ""}</ReactMarkdown>
      </div>
    </div>
  );
}

function ConfidenceBadge({ level, className = "" }) {
  const colors = {
    high: "bg-emerald-50 text-emerald-700 border-emerald-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    low: "bg-rose-50 text-rose-700 border-rose-200",
    unverified: "bg-slate-100 text-slate-600 border-slate-300",
  };
  const style = colors[level] || colors.unverified;
  return (
    <span className={`inline-flex items-center text-xs font-bold px-2.5 py-1 rounded-md border ${style} ${className}`}>
      {(level || "unverified").toUpperCase()}
    </span>
  );
}

const READINESS_DIMS = [
  { key: "deck_quality", label: "Deck Quality", icon: "📄" },
  { key: "market_opportunity", label: "Market Opportunity", icon: "🌍" },
  { key: "team_credibility", label: "Team Credibility", icon: "👥" },
  { key: "business_model_clarity", label: "Business Model Clarity", icon: "💰" },
  { key: "defensibility", label: "Defensibility", icon: "🛡️" },
];

function readinessColor(v) {
  if (v >= 8) return "text-emerald-400";
  if (v >= 6) return "text-indigo-400";
  if (v >= 4) return "text-amber-400";
  if (v >= 2) return "text-orange-400";
  return "text-rose-400";
}

function readinessBg(v) {
  if (v >= 8) return "bg-gradient-to-r from-emerald-500 to-teal-400";
  if (v >= 6) return "bg-gradient-to-r from-indigo-500 to-purple-500";
  if (v >= 4) return "bg-gradient-to-r from-amber-400 to-yellow-500";
  if (v >= 2) return "bg-gradient-to-r from-orange-400 to-red-500";
  return "bg-gradient-to-r from-rose-500 to-red-600";
}

function readinessLabel(v) {
  if (v >= 8) return "Investor Ready";
  if (v >= 6) return "Nearly Ready";
  if (v >= 4) return "Needs Work";
  return "Not Ready";
}

function InvestorReadinessCard({ readiness }) {
  const overall = readiness.overall;
  return (
    <div className="bg-white border border-slate-200 rounded-3xl p-8 relative overflow-hidden">
      <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl mix-blend-screen" />
      <div className="grid md:grid-cols-[1fr_2fr] gap-8 relative z-10">
        
        <div className="flex flex-col justify-center items-center md:items-start text-center md:text-left border-b md:border-b-0 md:border-r border-slate-200 pb-8 md:pb-0 md:pr-8">
          <h2 className="text-slate-600 font-semibold uppercase tracking-widest text-sm mb-4">Investor Readiness</h2>
          <div className={`text-7xl font-extrabold tracking-tighter mb-2 ${readinessColor(overall)} drop-shadow-lg`}>
            {overall.toFixed(1)}
          </div>
          <div className="text-slate-900 font-bold text-xl mb-1">{readinessLabel(overall)}</div>
          <div className="text-slate-9000 text-sm">Overall Score / 10</div>
        </div>

        <div className="space-y-4 flex flex-col justify-center">
          {READINESS_DIMS.map(({ key, label, icon }) => {
            const val = readiness[key] ?? 0;
            return (
              <div key={key} className="group">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-700 font-medium flex items-center gap-2"><span className="text-lg">{icon}</span> {label}</span>
                  <span className="text-slate-900 font-bold">{val.toFixed(1)}</span>
                </div>
                <div className="h-2.5 bg-slate-50 rounded-full overflow-hidden border border-slate-200 p-0.5">
                  <div
                    className={`h-full rounded-full transition-all duration-1000 ${readinessBg(val)} shadow-inner`}
                    style={{ width: `${val * 10}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
