import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AlertTriangle, CheckCircle, Sparkles, ArrowRight, Activity, Eye, XCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import StartupBadge from '../components/StartupBadge';

export default function PublicReportPage() {
  const { analysisId } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [simStarted, setSimStarted] = useState(false);
  const [revealed, setRevealed] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    loadReport();
  }, [analysisId]);

  // VC Simulator auto-reveal
  useEffect(() => {
    if (!simStarted || !report?.vc_impression?.length) return;
    if (revealed >= report.vc_impression.length) return;
    const timer = setTimeout(() => setRevealed(prev => prev + 1), 1200);
    return () => clearTimeout(timer);
  }, [revealed, simStarted, report]);

  async function loadReport() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/report/${analysisId}`);
      if (res.ok) {
        setReport(await res.json());
      } else if (res.status === 404) {
        setError('Report not found');
      } else {
        setError('Failed to load report');
      }
    } catch (err) {
      setError('Failed to load report');
      console.error(err);
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center">
        <div className="relative mb-6">
          <div className="w-16 h-16 border-4 border-slate-200 border-t-indigo-500 rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <Activity className="w-5 h-5 text-indigo-400 animate-pulse" />
          </div>
        </div>
        <div className="text-slate-600 text-lg font-medium">Retrieving Analysis...</div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="bg-white border border-slate-200 rounded-2xl p-10 max-w-md text-center shadow-xl">
          <div className="w-16 h-16 bg-rose-50 rounded-full flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="text-rose-500" size={32} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-3">Report Not Found</h1>
          <p className="text-slate-600 mb-8 leading-relaxed">
            This analysis report does not exist, has been removed, or is not set to public visibility.
          </p>
          <button onClick={() => navigate('/')} className="w-full bg-indigo-600 text-white px-6 py-3 rounded-xl hover:bg-indigo-500 transition-colors font-semibold">
            Return to Home
          </button>
        </motion.div>
      </div>
    );
  }

  const getScoreGradient = (score) => {
    if (score >= 8) return 'from-emerald-500 to-teal-600';
    if (score >= 6) return 'from-indigo-500 to-purple-600';
    if (score >= 4) return 'from-amber-500 to-orange-600';
    return 'from-rose-500 to-red-600';
  };

  const getScoreLabel = (score) => {
    if (score >= 8) return 'Investor Ready';
    if (score >= 6) return 'Promising';
    if (score >= 4) return 'Needs Work';
    return 'Major Gaps';
  };

  const getVCOutcome = (score) => {
    if (score >= 7) return { text: 'Lean Pass → Request Follow-up', color: 'text-emerald-600' };
    if (score >= 5) return { text: 'Likely Pass → Needs Major Fixes', color: 'text-amber-600' };
    return { text: 'Likely Reject → Deck Not Ready', color: 'text-rose-600' };
  };

  const shareUrl = window.location.href;
  const vcImpression = report.vc_impression || [];
  const outcome = getVCOutcome(report.investor_readiness_overall);

  return (
    <div className="min-h-screen bg-slate-50 relative overflow-hidden">
      {/* Background Glow */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 right-[-10%] w-[600px] h-[400px] bg-indigo-500/10 rounded-full blur-[120px]" />
      </div>

      {/* Header */}
      <div className="relative z-10 border-b border-slate-200 bg-white shadow-sm backdrop-blur-xl sticky top-0">
        <div className="max-w-5xl mx-auto px-6 py-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight flex items-center gap-3">
              {report.startup_name}
              <span className="text-xs font-semibold px-2 py-1 bg-slate-100 text-slate-600 rounded-full border border-slate-300/50">
                Public Report
              </span>
            </h1>
            <p className="text-slate-500 text-sm mt-1">VC Due Diligence & Readiness Analysis</p>
          </div>
          <button onClick={() => navigate('/')} className="hidden md:flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-sm text-white rounded-lg transition-colors font-medium">
            Analyze Your Deck
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-12 relative z-10">
        {/* Score + Badge — Two column on desktop */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {/* Main Score Card */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="md:col-span-2 bg-white border border-slate-200 rounded-[2rem] p-10 md:p-14 text-center relative overflow-hidden shadow-lg">
            <div className="relative z-10">
              <div className="inline-flex items-center justify-center gap-2 mb-6 px-4 py-1.5 rounded-full bg-slate-50 border border-slate-200">
                <Sparkles className="text-indigo-600 w-4 h-4" />
                <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wider">Investor Readiness</h2>
              </div>

              <div className={`text-8xl md:text-9xl font-extrabold tracking-tighter mb-2 bg-gradient-to-br ${getScoreGradient(report.investor_readiness_overall)} bg-clip-text text-transparent`}>
                {report.investor_readiness_overall.toFixed(1)}
              </div>

              <div className="text-lg font-semibold text-slate-600 mb-1">{getScoreLabel(report.investor_readiness_overall)}</div>
              <div className="text-sm text-slate-400 mb-4">out of 10.0</div>

              {/* Percentile Badge */}
              {report.percentile > 0 && report.total_analyses > 5 && (
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 border border-indigo-200 rounded-full mb-6">
                  <span className="text-sm font-bold text-indigo-600">Top {100 - report.percentile}%</span>
                  <span className="text-sm text-indigo-400">of {report.total_analyses} startups analyzed</span>
                </div>
              )}

              {/* Comparison Bar */}
              <div className="max-w-md mx-auto mt-4">
                <div className="flex justify-between text-xs text-slate-400 mb-2">
                  <span>Average startup: 5.9</span>
                  <span>Top startups: 8.5+</span>
                </div>
                <div className="h-4 bg-slate-100 rounded-full overflow-hidden relative border border-slate-200">
                  {/* Average marker */}
                  <div className="absolute top-0 bottom-0 w-px bg-slate-300" style={{ left: '59%' }} />
                  {/* Score bar */}
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(report.investor_readiness_overall / 10) * 100}%` }}
                    transition={{ duration: 1.5, ease: 'easeOut' }}
                    className={`h-full rounded-full bg-gradient-to-r ${getScoreGradient(report.investor_readiness_overall)}`}
                  />
                </div>
              </div>
            </div>
          </motion.div>

          {/* Shareable Badge Sidebar */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <StartupBadge
              startupName={report.startup_name}
              score={report.investor_readiness_overall}
              percentile={report.percentile || 0}
              totalAnalyses={report.total_analyses || 0}
              shareUrl={shareUrl}
            />
          </motion.div>
        </div>

        {/* VC First Impression Simulator */}
        {vcImpression.length > 0 && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm mb-8">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center">
                <Eye className="w-5 h-5 text-rose-500" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">VC First Impression Simulator</h3>
                <p className="text-xs text-slate-500">How investors react to this deck in 30 seconds</p>
              </div>
            </div>

            <div className="px-6 pb-6 pt-4">
              {!simStarted ? (
                <div className="text-center py-6">
                  <p className="text-slate-600 text-sm mb-4">Watch how a VC partner reacts slide-by-slide.</p>
                  <button
                    onClick={() => { setSimStarted(true); setRevealed(1); }}
                    className="px-6 py-3 bg-slate-900 text-white rounded-xl font-semibold text-sm hover:bg-slate-800 transition-colors cursor-pointer"
                  >
                    ▶ Start Simulation
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-3">
                    Investor opens the deck...
                  </div>

                  {vcImpression.slice(0, revealed).map((signal, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.4 }}
                      className={`${signal.severity === 'critical' ? 'bg-rose-50 border-rose-200' : 'bg-amber-50 border-amber-200'} border rounded-xl p-4`}
                    >
                      <div className="flex items-start gap-3">
                        <XCircle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${signal.severity === 'critical' ? 'text-rose-500' : 'text-amber-500'}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="text-xs font-bold text-slate-500">Slide {signal.slide}</span>
                            <span className="text-xs text-slate-400">—</span>
                            <span className="text-xs font-semibold text-slate-700 capitalize">{(signal.type || '').replace(/_/g, ' ')} Problem</span>
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              signal.severity === 'critical' ? 'bg-rose-100 text-rose-600' : 'bg-amber-100 text-amber-600'
                            }`}>
                              {signal.severity === 'critical' ? 'DEAL BREAKER' : 'RED FLAG'}
                            </span>
                          </div>
                          <p className="text-sm text-slate-700 font-medium">{signal.problem}</p>
                          <p className="text-xs text-slate-500 mt-1 italic">Investor thought: "{signal.reaction}"</p>
                        </div>
                      </div>
                    </motion.div>
                  ))}

                  {revealed >= vcImpression.length && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="mt-4 pt-4 border-t border-slate-200">
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-center">
                        <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-2">Final VC Reaction</div>
                        <div className={`text-lg font-bold ${outcome.color}`}>{outcome.text}</div>
                        <div className="text-xs text-slate-500 mt-2">
                          {vcImpression.length} rejection signal{vcImpression.length !== 1 ? 's' : ''} detected
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Two-column: Strengths + Risks */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          {/* Key Strengths */}
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="bg-emerald-50 border border-emerald-200 rounded-3xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <CheckCircle className="text-emerald-600" size={20} />
              </div>
              <h3 className="text-xl font-bold text-slate-900 tracking-tight">Key Strengths</h3>
            </div>
            <div className="space-y-4">
              {report.key_strengths.map((strength) => (
                <div key={strength.rank} className="bg-white border border-emerald-200 rounded-xl p-5">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-8 h-8 bg-emerald-100 text-emerald-600 border border-emerald-200 rounded-lg flex items-center justify-center text-sm font-bold">
                      {strength.rank}
                    </div>
                    <div className="flex-1 mt-1">
                      <div className="text-emerald-700 font-semibold text-sm mb-1.5 uppercase tracking-wide">
                        {strength.dimension.replace(/_/g, ' ')}
                      </div>
                      <div className="text-slate-700 text-sm leading-relaxed">{strength.description}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Primary Risks */}
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25 }} className="bg-rose-50 border border-rose-200 rounded-3xl p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-rose-100 rounded-lg">
                <AlertTriangle className="text-rose-600" size={20} />
              </div>
              <h3 className="text-xl font-bold text-slate-900 tracking-tight">Primary Risks</h3>
            </div>
            <div className="space-y-4">
              {report.deal_breakers.map((breaker) => (
                <div key={breaker.rank} className="bg-white border border-rose-200 rounded-xl p-5">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-8 h-8 bg-rose-100 text-rose-600 border border-rose-200 rounded-lg flex items-center justify-center text-sm font-bold">
                      {breaker.rank}
                    </div>
                    <div className="flex-1 mt-1">
                      <div className="text-rose-700 font-semibold text-sm mb-1.5 uppercase tracking-wide">
                        {breaker.category.replace(/_/g, ' ')}
                      </div>
                      <div className="text-slate-700 text-sm leading-relaxed">{breaker.description}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* CTA Section */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="relative bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-200 rounded-[2rem] p-10 md:p-14 text-center overflow-hidden">
          <div className="relative z-10 max-w-2xl mx-auto">
            <h3 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4 tracking-tight">
              Find out why investors will reject your startup.
            </h3>
            <p className="text-slate-600 text-lg mb-8">
              Upload your pitch deck. Get your score, deal breakers, and the exact VC reaction in 30 seconds.
            </p>
            <button
              onClick={() => navigate('/')}
              className="group inline-flex items-center gap-2 bg-indigo-600 text-white px-8 py-4 rounded-xl font-bold hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/20"
            >
              Analyze My Deck Free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </button>
            <p className="text-sm text-slate-500 mt-4">3 free analyses. No credit card.</p>
          </div>
        </motion.div>

        {/* Footer */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }} className="mt-16 text-center border-t border-slate-200 pt-8">
          <div className="flex items-center justify-center gap-2 mb-2 font-bold text-slate-900">
            <div className="w-5 h-5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded flex items-center justify-center">
              <div className="w-2.5 h-2.5 border-2 border-white rounded-sm" />
            </div>
            Venture Intelligence Engine
          </div>
          <p className="text-slate-500 text-xs">
            Analysis generated on {new Date(report.created_at).toLocaleDateString()}
          </p>
        </motion.div>
      </div>
    </div>
  );
}
